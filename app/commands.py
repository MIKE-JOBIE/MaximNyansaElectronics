import click
from datetime import date, timedelta
from flask.cli import with_appcontext
from .extensions import db
from .models import User, Program, Category, Product, Resource, Post
from .utils import slugify

def register_commands(app):
    @app.cli.command("seed")
    @with_appcontext
    def seed():
        """Create admin, sample programs, categories, products."""
        from flask import current_app
        admin_email = current_app.config["ADMIN_EMAIL"]
        admin_pass  = current_app.config["ADMIN_PASSWORD"]

        if not User.query.filter_by(email=admin_email).first():
            u = User(email=admin_email, first_name="Admin", last_name="Maxim", role="admin")
            u.set_password(admin_pass)
            db.session.add(u)
            click.echo(f"✔ Admin created: {admin_email}")

        if Program.query.count() == 0:
            p1 = Program(
                title="3-Month Electronics Repair Boot Camp",
                slug=slugify("3-Month Electronics Repair Boot Camp"),
                summary="Hands-on training in repair, replacement & maintenance.",
                description=("A practical, 90% hands-on training programme covering "
                             "electronics fundamentals, component testing, soldering, "
                             "board-level repair, and entrepreneurship."),
                start_date=date.today()+timedelta(days=30),
                end_date=date.today()+timedelta(days=120),
                capacity=20, fee=0, status="open")
            p2 = Program(
                title="Mobile Phone Repair Intensive",
                slug=slugify("Mobile Phone Repair Intensive"),
                summary="Deep-dive into smartphone repair and diagnostics.",
                description="Focused 6-week track for those who want to specialize in mobile repair.",
                start_date=date.today()+timedelta(days=45),
                end_date=date.today()+timedelta(days=90),
                capacity=15, fee=0, status="open")
            p3 = Program(
                title="Laptop & Desktop Maintenance",
                slug=slugify("Laptop & Desktop Maintenance"),
                summary="From diagnostics to motherboard-level repair.",
                description="Advanced track covering laptops and desktops including board-level repair.",
                start_date=date.today()+timedelta(days=60),
                end_date=date.today()+timedelta(days=150),
                capacity=12, fee=0, status="open")
            db.session.add_all([p1, p2, p3])
            click.echo("✔ Programs seeded")

        cats = ["Laptops", "Phones", "Accessories", "Tools"]
        for c in cats:
            if not Category.query.filter_by(name=c).first():
                db.session.add(Category(name=c, slug=slugify(c)))
        db.session.commit()

        if Product.query.count() == 0:
            cat = Category.query.first()
            samples = [
                ("Refurbished HP Laptop", "HP EliteBook 840 G5, 8GB RAM, 256GB SSD — professionally refurbished.", 2500, "refurbished"),
                ("Digital Multimeter", "Reliable multimeter for diagnostics and testing.", 180, "new"),
                ("Soldering Kit Pro", "60W adjustable soldering station with accessories.", 420, "new"),
                ("Refurbished iPhone X", "64GB, fully tested, 90-day warranty.", 1900, "refurbished"),
            ]
            for name, desc, price, cond in samples:
                db.session.add(Product(
                    name=name, slug=slugify(name), description=desc,
                    price=price, stock=10, condition=cond,
                    category_id=cat.id, is_active=True))
            click.echo("✔ Sample products seeded")

        if Resource.query.count() == 0:
            for t, c in [("Electronics Fundamentals Handbook", "Handbook"),
                         ("Soldering Best Practices", "Guide"),
                         ("Board-Level Repair Manual", "Manual"),
                         ("Starting Your Repair Business", "Entrepreneurship")]:
                db.session.add(Resource(title=t, slug=slugify(t),
                    description=f"Reference material — {t}", category=c,
                    file_url="#"))
            click.echo("✔ E-Library seeded")

        if Post.query.count() == 0:
            db.session.add(Post(
                title="First cohort graduates 13 trainees",
                slug=slugify("First cohort graduates 13 trainees"),
                body="Our first Vocational Training Programme in Electronic Repairs and Maintenance has successfully completed with 13 trainees. Approximately 90% of learning was practical."))
        db.session.commit()
        click.echo("✅ Seed complete.")