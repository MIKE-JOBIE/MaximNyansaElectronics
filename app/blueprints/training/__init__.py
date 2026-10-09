from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from ...models import Program, Application
from ...forms import ApplicationForm
from ...extensions import db
from sqlalchemy.exc import IntegrityError

training_bp = Blueprint("training", __name__, template_folder="../../templates/training")

@training_bp.route("/")
def index():
    programs = Program.query.order_by(Program.created_at.desc()).all()
    return render_template("training/index.html", programs=programs)

@training_bp.route("/program/<slug>")
def program_detail(slug):
    p = Program.query.filter_by(slug=slug).first_or_404()
    return render_template("training/program_detail.html", program=p)

@training_bp.route("/apply", methods=["GET","POST"])
@login_required
def apply():
    program_id = request.args.get("program_id", type=int)
    programs = Program.query.filter_by(status="open").all()
    if not programs:
        flash("No programs are currently open.", "warning"); return redirect(url_for("training.index"))
    form = ApplicationForm()
    form.program_id = program_id  # attach dynamically
    if form.validate_on_submit():
        pid = request.form.get("program_id", type=int)
        program = (Program.query.filter_by(id=pid, status="open")
                   .with_for_update().first()) if pid else None
        if program is None:
            flash("Please choose a program that is open for applications.", "warning")
            return redirect(url_for("training.apply"))
        taken = Application.query.filter(Application.program_id == pid,
                                         Application.status.in_(["pending", "approved", "enrolled"])).count()
        if program.capacity and taken >= program.capacity:
            flash("Sorry, this program is full. Please check back for the next intake.", "warning")
            return redirect(url_for("training.index"))
        existing = Application.query.filter_by(user_id=current_user.id, program_id=pid)\
                    .filter(Application.status.in_(["pending","approved","enrolled"])).first()
        if existing:
            flash("You already have an active application for this program.", "warning")
            return redirect(url_for("training.my_applications"))
        app_obj = Application(user_id=current_user.id, program_id=pid,
                              motivation=form.motivation.data, education=form.education.data,
                              address=form.address.data, phone=form.phone.data)
        db.session.add(app_obj)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("You already have an active application for this program.", "warning")
            return redirect(url_for("training.my_applications"))
        flash("Application submitted! We'll be in touch.", "success")
        return redirect(url_for("training.my_applications"))
    return render_template("training/apply.html", form=form, programs=programs, selected_program=program_id)

@training_bp.route("/my-applications")
@login_required
def my_applications():
    page = request.args.get("page", 1, type=int)
    pagination = (Application.query.filter_by(user_id=current_user.id)
                  .order_by(Application.submitted_at.desc())
                  .paginate(page=page, per_page=20, error_out=False))
    return render_template("training/my_applications.html", applications=pagination.items, pagination=pagination)

@training_bp.route("/online-venue")
def online_venue():
    return render_template("training/online_venue.html")
