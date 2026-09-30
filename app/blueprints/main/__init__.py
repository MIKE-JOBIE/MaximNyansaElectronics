from flask import Blueprint, render_template, request, flash, redirect, url_for
from ...models import Post, Program, Message
from ...forms import ContactForm
from ...extensions import db
from ...models import Post, Program, Message, User, Application, Order, Donation, Product, Resource



main_bp = Blueprint("main", __name__, template_folder="../../templates/main")

@main_bp.route("/")
def index():
    programs = Program.query.filter_by(status="open").order_by(Program.created_at.desc()).limit(3).all()
    posts = Post.query.order_by(Post.published_at.desc()).limit(3).all()
    return render_template("main/index.html", programs=programs, posts=posts)

@main_bp.route("/about")
def about(): return render_template("main/about.html")

@main_bp.route("/news")
def news(): return render_template("main/news.html", posts=Post.query.order_by(Post.published_at.desc()).all())

@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        db.session.add(Message(name=form.name.data, email=form.email.data,
                               subject=form.subject.data, body=form.message.data))
        db.session.commit()
        flash("Thanks! We'll get back to you soon.", "success")
        return redirect(url_for("main.contact"))
    return render_template("main/contact.html", form=form)

@main_bp.route("/impact")
def impact():
    from sqlalchemy import func
    from ...settings_utils import get_all_settings
    site = get_all_settings()

    stats = {
        "trained":   site.get("impact_trained", "13"),
        "practical": site.get("impact_practical", "90"),
        "kits":      site.get("impact_kits", "10"),
        "target":    site.get("impact_target", "80"),
        "users":     User.query.count(),
        "applications": Application.query.count(),
        "enrolled":  Application.query.filter_by(status="enrolled").count(),
        "programs":  Program.query.count(),
        "products":  Product.query.count(),
        "orders":    Order.query.count(),
        "donations_total": float(
            db.session.query(func.coalesce(func.sum(Donation.amount), 0)).scalar()
        ),
    }
    return render_template("main/impact.html", stats=stats, site=site)

@main_bp.route("/health")
def health():
    from flask import jsonify
    from ...extensions import db
    from sqlalchemy import text
    try:
        db.session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return jsonify({
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "app": "maxim-nyansa-electronics",
    }), (200 if db_ok else 503)