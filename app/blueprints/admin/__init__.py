from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from ...models import (User, Program, Application, Product, Category,
                       Order, Resource, Donation, Message, Post)
from ...forms import ProgramForm, ProductForm, ResourceForm
from ...extensions import db
from ...utils import slugify, save_upload
from sqlalchemy import func
from .settings_routes import register_settings_routes
from ...forms import ProgramForm, ProductForm, ResourceForm, PostForm
from .bulk_routes import register_bulk_routes

from flask import send_file
from io import BytesIO
from ...certificate import generate_certificate

admin_bp = Blueprint("admin", __name__, template_folder="../../templates/admin")

def admin_required(f):
    @wraps(f)
    def w(*a, **kw):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*a, **kw)
    return w

from datetime import datetime, timedelta
from sqlalchemy import func

@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    stats = {
        "users": User.query.count(),
        "applications": Application.query.count(),
        "pending": Application.query.filter_by(status="pending").count(),
        "programs": Program.query.count(),
        "products": Product.query.count(),
        "orders": Order.query.count(),
        "messages": Message.query.filter_by(is_read=False).count(),
        "donations_total": float(db.session.query(func.coalesce(func.sum(Donation.amount), 0)).scalar()),
    }
    recent_apps = Application.query.order_by(Application.submitted_at.desc()).limit(6).all()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(6).all()

    # Chart data — applications per day for last 14 days
    today = datetime.utcnow().date()
    days = [(today - timedelta(days=i)) for i in range(13, -1, -1)]
    chart_apps = {"labels": [d.strftime("%b %d") for d in days], "values": []}
    for d in days:
        count = Application.query.filter(
            func.date(Application.submitted_at) == d
        ).count()
        chart_apps["values"].append(count)

    # Chart data — status breakdown
    status_counts = dict(
        db.session.query(Application.status, func.count(Application.id))
        .group_by(Application.status).all()
    )
    statuses = ["pending", "approved", "enrolled", "rejected"]
    chart_status = {
        "labels": [s.title() for s in statuses if s in status_counts],
        "values": [status_counts.get(s, 0) for s in statuses if s in status_counts],
    }
    if not chart_status["labels"]:
        chart_status = {"labels": ["No data"], "values": [0]}

    return render_template("admin/dashboard.html",
                           stats=stats,
                           recent_apps=recent_apps,
                           recent_orders=recent_orders,
                           chart_apps=chart_apps,
                           chart_status=chart_status)

# --- APPLICATIONS ---
@admin_bp.route("/applications")
@login_required
@admin_required
def applications():
    status = request.args.get("status")
    q = Application.query
    if status: q = q.filter_by(status=status)
    apps = q.order_by(Application.submitted_at.desc()).all()
    return render_template("admin/applications.html", applications=apps, status=status)

@admin_bp.route("/applications/<int:aid>/<action>", methods=["POST"])
@login_required
@admin_required
def application_action(aid, action):
    a = Application.query.get_or_404(aid)
    if action in ("approve","reject","enroll"):
        a.status = {"approve":"approved","reject":"rejected","enroll":"enrolled"}[action]
        a.reviewed_at = datetime.utcnow()
        db.session.commit()
        flash(f"Application {a.status}.", "success")
    return redirect(url_for("admin.applications"))

# --- PROGRAMS ---
@admin_bp.route("/programs")
@login_required
@admin_required
def programs():
    return render_template("admin/programs.html", programs=Program.query.order_by(Program.created_at.desc()).all())

@admin_bp.route("/programs/new", methods=["GET","POST"])
@login_required
@admin_required
def program_new():
    form = ProgramForm()
    if form.validate_on_submit():
        img = save_upload(form.cover_image.data, "prog_")
        p = Program(title=form.title.data, slug=slugify(form.title.data),
                    summary=form.summary.data, description=form.description.data,
                    capacity=form.capacity.data, fee=form.fee.data,
                    status=form.status.data, cover_image=img)
        db.session.add(p); db.session.commit()
        flash("Program created.", "success")
        return redirect(url_for("admin.programs"))
    return render_template("admin/program_form.html", form=form, program=None)

@admin_bp.route("/programs/<int:pid>/edit", methods=["GET","POST"])
@login_required
@admin_required
def program_edit(pid):
    p = Program.query.get_or_404(pid)
    form = ProgramForm(obj=p)
    if form.validate_on_submit():
        p.title=form.title.data; p.slug=slugify(form.title.data)
        p.summary=form.summary.data; p.description=form.description.data
        p.capacity=form.capacity.data; p.fee=form.fee.data; p.status=form.status.data
        img = save_upload(form.cover_image.data, "prog_")
        if img: p.cover_image = img
        db.session.commit(); flash("Program updated.","success")
        return redirect(url_for("admin.programs"))
    return render_template("admin/program_form.html", form=form, program=p)

# --- PRODUCTS ---
@admin_bp.route("/products")
@login_required
@admin_required
def products():
    return render_template("admin/products.html", products=Product.query.order_by(Product.created_at.desc()).all())

@admin_bp.route("/products/new", methods=["GET","POST"])
@login_required
@admin_required
def product_new():
    form = ProductForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    if form.validate_on_submit():
        img = save_upload(form.image.data, "prod_")
        p = Product(name=form.name.data, slug=slugify(form.name.data),
                    description=form.description.data, price=form.price.data,
                    stock=form.stock.data, condition=form.condition.data,
                    category_id=form.category_id.data, image=img,
                    is_active=(form.is_active.data=="yes"))
        db.session.add(p); db.session.commit()
        flash("Product created.", "success")
        return redirect(url_for("admin.products"))
    return render_template("admin/product_form.html", form=form, product=None)

@admin_bp.route("/products/<int:pid>/edit", methods=["GET","POST"])
@login_required
@admin_required
def product_edit(pid):
    p = Product.query.get_or_404(pid)
    form = ProductForm(obj=p)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    if request.method == "GET":
        form.is_active.data = "yes" if p.is_active else "no"
    if form.validate_on_submit():
        p.name=form.name.data; p.slug=slugify(form.name.data)
        p.description=form.description.data; p.price=form.price.data
        p.stock=form.stock.data; p.condition=form.condition.data
        p.category_id=form.category_id.data; p.is_active=(form.is_active.data=="yes")
        img = save_upload(form.image.data, "prod_")
        if img: p.image = img
        db.session.commit(); flash("Product updated.","success")
        return redirect(url_for("admin.products"))
    return render_template("admin/product_form.html", form=form, product=p)

# --- ORDERS ---
@admin_bp.route("/orders")
@login_required
@admin_required
def orders():
    return render_template("admin/orders.html", orders=Order.query.order_by(Order.created_at.desc()).all())

@admin_bp.route("/orders/<int:oid>/<status>", methods=["POST"])
@login_required
@admin_required
def order_status(oid, status):
    o = Order.query.get_or_404(oid)
    if status in ("pending","paid","shipped","delivered","cancelled"):
        o.status = status; db.session.commit()
        flash(f"Order marked {status}.", "success")
    return redirect(url_for("admin.orders"))

# --- MESSAGES ---
@admin_bp.route("/messages")
@login_required
@admin_required
def messages():
    return render_template("admin/messages.html", messages=Message.query.order_by(Message.created_at.desc()).all())

@admin_bp.route("/messages/<int:mid>/read", methods=["POST"])
@login_required
@admin_required
def message_read(mid):
    m = Message.query.get_or_404(mid); m.is_read = True; db.session.commit()
    return redirect(url_for("admin.messages"))

# --- RESOURCES ---
@admin_bp.route("/resources", methods=["GET","POST"])
@login_required
@admin_required
def resources():
    form = ResourceForm()
    if form.validate_on_submit():
        url = form.file_url.data or ""
        if form.file.data and form.file.data.filename:
            url = "/static/" + save_upload(form.file.data, "lib_")
        r = Resource(title=form.title.data, slug=slugify(form.title.data),
                     description=form.description.data, category=form.category.data,
                     file_url=url)
        db.session.add(r); db.session.commit()
        flash("Resource added.", "success")
        return redirect(url_for("admin.resources"))
    return render_template("admin/resources.html",
                           resources=Resource.query.order_by(Resource.created_at.desc()).all(),
                           form=form)

# --- DONATIONS ---
@admin_bp.route("/donations")
@login_required
@admin_required
def donations():
    return render_template("admin/donations.html", donations=Donation.query.order_by(Donation.created_at.desc()).all())

@admin_bp.route("/donations/<int:did>/verify", methods=["POST"])
@login_required
@admin_required
def donation_verify(did):
    d = Donation.query.get_or_404(did); d.verified = True; db.session.commit()
    return redirect(url_for("admin.donations"))

register_settings_routes(admin_bp)

# --- NEWS / BLOG ---
@admin_bp.route("/news")
@login_required
@admin_required
def news():
    posts = Post.query.order_by(Post.published_at.desc()).all()
    return render_template("admin/news.html", posts=posts)


@admin_bp.route("/news/new", methods=["GET", "POST"])
@login_required
@admin_required
def news_new():
    form = PostForm()
    if form.validate_on_submit():
        img = save_upload(form.cover_image.data, "post_")
        p = Post(title=form.title.data, slug=slugify(form.title.data),
                 body=form.body.data, cover_image=img)
        db.session.add(p); db.session.commit()
        flash("Post published.", "success")
        return redirect(url_for("admin.news"))
    return render_template("admin/news_form.html", form=form, post=None)


@admin_bp.route("/news/<int:pid>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def news_edit(pid):
    p = Post.query.get_or_404(pid)
    form = PostForm(obj=p)
    if form.validate_on_submit():
        p.title = form.title.data
        p.slug  = slugify(form.title.data)
        p.body  = form.body.data
        img = save_upload(form.cover_image.data, "post_")
        if img: p.cover_image = img
        db.session.commit()
        flash("Post updated.", "success")
        return redirect(url_for("admin.news"))
    return render_template("admin/news_form.html", form=form, post=p)


@admin_bp.route("/news/<int:pid>/delete", methods=["POST"])
@login_required
@admin_required
def news_delete(pid):
    p = Post.query.get_or_404(pid)
    db.session.delete(p); db.session.commit()
    flash("Post deleted.", "info")
    return redirect(url_for("admin.news"))

# --- CERTIFICATES ---
@admin_bp.route("/programs/<int:pid>/graduates")
@login_required
@admin_required
def program_graduates(pid):
    p = Program.query.get_or_404(pid)
    grads = Application.query.filter_by(program_id=pid, status="enrolled")\
                             .order_by(Application.submitted_at).all()
    return render_template("admin/graduates.html", program=p, graduates=grads)


@admin_bp.route("/applications/<int:aid>/certificate")
@login_required
@admin_required
def certificate_download(aid):
    a = Application.query.get_or_404(aid)
    if a.status not in ("enrolled", "approved"):
        flash("Certificate only available for approved or enrolled trainees.", "warning")
        return redirect(url_for("admin.applications"))

    pdf_bytes = generate_certificate(a.applicant.full_name, a.program.title)
    filename = f"certificate_{a.id}_{a.applicant.last_name or 'trainee'}.pdf"
    return send_file(BytesIO(pdf_bytes), mimetype="application/pdf",
                     as_attachment=True, download_name=filename)

register_bulk_routes(admin_bp)