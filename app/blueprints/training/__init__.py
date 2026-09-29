from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from ...models import Program, Application
from ...forms import ApplicationForm
from ...extensions import db

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
        pid = int(request.form.get("program_id"))
        existing = Application.query.filter_by(user_id=current_user.id, program_id=pid)\
                    .filter(Application.status.in_(["pending","approved","enrolled"])).first()
        if existing:
            flash("You already have an active application for this program.", "warning")
            return redirect(url_for("training.my_applications"))
        app_obj = Application(user_id=current_user.id, program_id=pid,
                              motivation=form.motivation.data, education=form.education.data,
                              address=form.address.data, phone=form.phone.data)
        db.session.add(app_obj); db.session.commit()
        flash("Application submitted! We'll be in touch.", "success")
        return redirect(url_for("training.my_applications"))
    return render_template("training/apply.html", form=form, programs=programs, selected_program=program_id)

@training_bp.route("/my-applications")
@login_required
def my_applications():
    apps = Application.query.filter_by(user_id=current_user.id).order_by(Application.submitted_at.desc()).all()
    return render_template("training/my_applications.html", applications=apps)

@training_bp.route("/online-venue")
def online_venue():
    return render_template("training/online_venue.html")

# import request at end to avoid circular lint
from flask import request