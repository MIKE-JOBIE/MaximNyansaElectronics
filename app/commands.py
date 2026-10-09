import click
from datetime import date, timedelta, datetime
from flask.cli import with_appcontext
from .extensions import db
from .models import User, Program, Category, Product, Resource, Post, Order
from .utils import slugify


def register_commands(app):
    @app.cli.command("seed")
    @with_appcontext
    def seed():
        """Create admin, sample programs, categories, products."""
        from flask import current_app

        admin_email = current_app.config["ADMIN_EMAIL"]
        admin_pass = current_app.config["ADMIN_PASSWORD"]

        # ─── SITE SETTINGS ──────────────────────────────────
        try:
            from .settings_utils import seed_default_settings
            seed_default_settings()
            click.echo("✔ Site settings seeded")
        except Exception as e:
            click.echo(f"⚠ Settings seed skipped: {e}")

        # ─── ADMIN USER ─────────────────────────────────────
        if not User.query.filter_by(email=admin_email).first():
            u = User(email=admin_email, first_name="Admin", last_name="Maxim", role="admin")
            u.set_password(admin_pass)
            db.session.add(u)
            click.echo(f"✔ Admin created: {admin_email}")
        else:
            click.echo(f"ℹ Admin already exists: {admin_email}")

        # ─── PROGRAMS ───────────────────────────────────────
        if Program.query.count() == 0:
            p1 = Program(
                title="3-Month Electronics Repair, Replacement & Maintenance Boot Camp",
                slug=slugify("3-Month Electronics Repair Replacement Maintenance Boot Camp"),
                summary="Hands-on training in electronics repair, replacement & maintenance. 90% practical, 3 months, up to 20 seats.",
                description=(
                    "A practical, hands-on training designed for underprivileged youth "
                    "(18-35 years) who are passionate about changing their situation, "
                    "acquiring new skills, becoming entrepreneurs, and serving their communities.\n\n"
                    "TRAINING INCLUDES:\n"
                    "- Electronics Fundamentals\n"
                    "- Components Testing\n"
                    "- Soldering & Desoldering\n"
                    "- Board Level Repair\n"
                    "- Tools & Equipment Handling\n"
                    "- Business & Entrepreneurship\n\n"
                    "GRADUATES RECEIVE:\n"
                    "- Certificate of Completion\n"
                    "- Entrepreneurship Guidance\n"
                    "- Career Support\n"
                    "- Starter Kit (for outstanding trainees)\n\n"
                    "CURRICULUM:\n"
                    "- Laptop & Desktop Repair\n"
                    "- Mobile Phone Repair\n"
                    "- Electronic Troubleshooting\n"
                    "- Flat TV Repair"
                ),
                start_date=date.today() + timedelta(days=30),
                end_date=date.today() + timedelta(days=120),
                capacity=20,
                fee=0,
                status="open",
            )
            p2 = Program(
                title="NGO Staff & Volunteers - One Week Practical ICT Training",
                slug=slugify("NGO Staff Volunteers One Week Practical ICT Training"),
                summary="Stop struggling with everyday digital tasks. One-week hands-on ICT boot camp for NGO staff, volunteers, and field officers.",
                description=(
                    "One-week practical ICT training designed for NGO staff, volunteers, "
                    "field officers, program coordinators, and project teams working with digital tools.\n\n"
                    "PRACTICAL SKILLS YOU WILL LEARN:\n"
                    "- Microsoft Word - Reports & Letters\n"
                    "- Microsoft Excel - Data & Basic Formulas\n"
                    "- PowerPoint - Presentations that Inspire\n"
                    "- Email & Internet - Effective Communication\n"
                    "- Google Workspace - Docs, Sheets, Drive\n"
                    "- Data Management & File Organization\n"
                    "- Online Safety & Digital Best Practices\n"
                    "- Using AI Tools to Work Smarter\n\n"
                    "BONUS MODULES:\n"
                    "- Using WhatsApp Business for Communication\n"
                    "- Cloud Storage & Collaboration\n"
                    "- Digital Tools for Project Management\n"
                    "- Creating Forms & Surveys (Google Forms)\n"
                    "- Document Templates & Automation Tips\n\n"
                    "DURATION: One Week (5 Training Days)\n"
                    "FORMAT: Hands-on practical sessions, interactive, small class size\n\n"
                    "YOU WILL RECEIVE:\n"
                    "- Certificate of Participation\n"
                    "- Resources\n"
                    "- Ongoing Support\n\n"
                    "TIME: 9:00 AM - 4:00 PM\n"
                    "LOCATION: 5C BaiBureh Road, Ferry Junction, Freetown"
                ),
                start_date=date.today() + timedelta(days=45),
                end_date=date.today() + timedelta(days=52),
                capacity=15,
                fee=400,
                status="open",
            )
            db.session.add_all([p1, p2])
            click.echo("✔ Programs seeded")
        else:
            click.echo(f"ℹ Programs already exist ({Program.query.count()})")

        # ─── CATEGORIES ─────────────────────────────────────
        cats = ["Laptops", "Phones", "Accessories", "Tools"]
        for c in cats:
            if not Category.query.filter_by(name=c).first():
                db.session.add(Category(name=c, slug=slugify(c)))
        db.session.commit()

        # ─── PRODUCTS ───────────────────────────────────────
        if Product.query.count() == 0:
            cat = Category.query.first()
            if cat:
                samples = [
                    ("Refurbished HP Laptop", "HP EliteBook 840 G5, 8GB RAM, 256GB SSD - professionally refurbished.", 2500, "refurbished"),
                    ("Digital Multimeter", "Reliable multimeter for diagnostics and testing.", 180, "new"),
                    ("Soldering Kit Pro", "60W adjustable soldering station with accessories.", 420, "new"),
                    ("Refurbished iPhone X", "64GB, fully tested, 90-day warranty.", 1900, "refurbished"),
                ]
                for name, desc, price, cond in samples:
                    db.session.add(Product(
                        name=name,
                        slug=slugify(name),
                        description=desc,
                        price=price,
                        stock=10,
                        condition=cond,
                        category_id=cat.id,
                        is_active=True,
                    ))
                click.echo("✔ Sample products seeded")

        # ─── E-LIBRARY ──────────────────────────────────────
        if Resource.query.count() == 0:
            resources = [
                ("Electronics Fundamentals Handbook", "Handbook"),
                ("Soldering Best Practices", "Guide"),
                ("Board-Level Repair Manual", "Manual"),
                ("Starting Your Repair Business", "Entrepreneurship"),
            ]
            for t, c in resources:
                db.session.add(Resource(
                    title=t,
                    slug=slugify(t),
                    description=f"Reference material - {t}",
                    category=c,
                    file_url="#",
                ))
            click.echo("✔ E-Library seeded")

        # ─── NEWS ───────────────────────────────────────────
        if Post.query.count() == 0:
            db.session.add(Post(
                title="First cohort graduates 13 trainees",
                slug=slugify("First cohort graduates 13 trainees"),
                body=(
                    "Our first Vocational Training Programme in Electronic Repairs and Maintenance "
                    "has successfully completed with 13 trainees. Approximately 90% of learning was practical."
                ),
            ))
            click.echo("✔ News post seeded")

        db.session.commit()
        click.echo("✅ Seed complete.")

    @app.cli.command("release-stale-orders")
    @click.option("--minutes", default=60, show_default=True, type=int, help="Cancel unpaid orders older than this many minutes.")
    @with_appcontext
    def release_stale_orders(minutes):
        """Release stock reserved by abandoned unpaid orders."""
        from .blueprints.shop import restore_order_stock
        from flask import current_app
        from sqlalchemy import and_
        cutoff = datetime.utcnow() - timedelta(minutes=max(5, minutes))
        orders = (Order.query.filter(Order.status == "pending",
                                     Order.payment_status.in_(["unpaid", "initiated", "failed"]),
                                     Order.created_at < cutoff)
                  .with_for_update().all())
        released = 0
        for order in orders:
            restore_order_stock(order)
            order.status = "cancelled"
            order.payment_status = "expired"
            released += 1
        db.session.commit()
        current_app.logger.info("Released stock from %s stale orders", released)
        click.echo(f"Released {released} stale order(s).")
