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

@main_bp.route("/robots.txt")
def robots():
    from flask import Response, url_for
    sitemap = url_for("main.sitemap", _external=True)
    body = f"User-agent: *\nAllow: /\nSitemap: {sitemap}\n"
    return Response(body, mimetype="text/plain")


@main_bp.route("/sitemap.xml")
def sitemap():
    from flask import Response, url_for
    from ...models import Program, Product, Post, Resource

    static_urls = [
        url_for("main.index", _external=True),
        url_for("main.about", _external=True),
        url_for("main.impact", _external=True),
        url_for("main.contact", _external=True),
        url_for("training.index", _external=True),
        url_for("shop.index", _external=True),
        url_for("library.index", _external=True),
        url_for("library.videos", _external=True),
        url_for("donors.index", _external=True),
    ]
    dynamic = []
    for p in Program.query.all():
        dynamic.append(url_for("training.program_detail", slug=p.slug, _external=True))
    for p in Product.query.filter_by(is_active=True).all():
        dynamic.append(url_for("shop.product_detail", slug=p.slug, _external=True))
    for r in Resource.query.all():
        dynamic.append(url_for("library.resource", slug=r.slug, _external=True))

    urls = "\n".join(f"  <url><loc>{u}</loc></url>" for u in (static_urls + dynamic))
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>'
    return Response(xml, mimetype="application/xml")

@main_bp.route("/favicon.ico")
def favicon():
    from flask import send_from_directory, current_app
    import os
    return send_from_directory(
        os.path.join(current_app.root_path, "static", "img"),
        "favicon.svg",
        mimetype="image/svg+xml",
    )

@main_bp.route("/developer")
def developer():
    return render_template("main/developer.html")