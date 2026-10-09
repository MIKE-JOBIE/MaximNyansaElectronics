import hmac
import logging
import os
import sys
from flask import Flask, render_template, current_app, request, abort
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from .extensions import db, migrate, login_manager, csrf, mail
from config import DevelopmentConfig, ProductionConfig, TestingConfig


def _validate_production(app):
    """Refuse to start in production with unsafe defaults."""
    problems = []
    key = app.config.get("SECRET_KEY", "") or ""
    if len(key) < 32 or "change-me" in key.lower() or key.lower().startswith(("dev-", "replace", "generate")):
        problems.append("SECRET_KEY must be a random string of at least 32 characters")
    if str(app.config.get("SQLALCHEMY_DATABASE_URI", "")).startswith("sqlite"):
        problems.append("DATABASE_URL must point to PostgreSQL (SQLite on a server loses data)")
    if problems:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))
    admin_pw = app.config.get("ADMIN_PASSWORD", "") or ""
    if admin_pw in ("", "ChangeMe123!") or len(admin_pw) < 12:
        app.logger.warning("ADMIN_PASSWORD is weak or default - set a strong one before running `flask seed`.")


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    if config_object:
        app.config.from_object(config_object)
    else:
        env = os.getenv("FLASK_ENV", "development")
        app.config.from_object(ProductionConfig if env == "production" else DevelopmentConfig)

    is_prod = app.config.get("ENV_NAME") == "production"
    if is_prod:
        _validate_production(app)
        n = app.config.get("TRUSTED_PROXY_COUNT", 1)
        if n > 0:
            # Behind Render/Heroku/nginx: trust forwarded client IP, scheme and host
            app.wsgi_app = ProxyFix(app.wsgi_app, x_for=n, x_proto=n, x_host=n)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # ─── BLUEPRINTS ────────────────────────────────────────
    from .blueprints.main     import main_bp
    from .blueprints.auth     import auth_bp
    from .blueprints.training import training_bp
    from .blueprints.shop     import shop_bp
    from .blueprints.library  import library_bp
    from .blueprints.donors   import donors_bp
    from .blueprints.admin    import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp,     url_prefix="/auth")
    app.register_blueprint(training_bp, url_prefix="/training")
    app.register_blueprint(shop_bp,     url_prefix="/shop")
    app.register_blueprint(library_bp,  url_prefix="/library")
    app.register_blueprint(donors_bp,   url_prefix="/donors")
    app.register_blueprint(admin_bp,    url_prefix="/admin")

    # ─── USER LOADER ───────────────────────────────────────
    from .models import User

    @login_manager.user_loader
    def load_user(uid):
        # Session id looks like "<id>:<tag>". The tag changes whenever the password
        # changes, so a password reset/change signs out every other session.
        raw_id, _, tag = str(uid).partition(":")
        try:
            user = db.session.get(User, int(raw_id))
        except (ValueError, TypeError):
            return None
        if user is None or not user.is_active_flag:
            return None
        return user if hmac.compare_digest(tag, user.session_tag) else None

    # ─── CART COUNT HELPER ─────────────────────────────────
    def _cart_count():
        from flask import session
        try:
            cart = session.get("cart", {})
            return sum(cart.values())
        except Exception:
            return 0

    # ─── GLOBAL CONTEXT ────────────────────────────────────
    @app.context_processor
    def inject_globals():
        from datetime import datetime
        from flask import request as _req
        from .settings_utils import get_all_settings
        try:
            site = get_all_settings()
        except Exception:
            site = {}
        return {
            "request": _req,
            "current_year": datetime.utcnow().year,
            "cart_count": _cart_count(),
            "brand_name":    site.get("brand_name", "Maxim Nyansa Electronics"),
            "brand_phone":   site.get("brand_phone", "+232 31 950 662"),
            "brand_email":   site.get("brand_email", "info@maximnyansa.com"),
            "brand_address": site.get("brand_address", "Freetown, Sierra Leone"),
            "brand_tagline": site.get("brand_tagline", "Skills Today, Success Tomorrow"),
            "site": site,
        }

    # ─── CLI COMMANDS ──────────────────────────────────────
    from .commands import register_commands
    register_commands(app)

    from .backup import register_backup_commands
    register_backup_commands(app)

    # ─── ERROR HANDLERS ────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(429)
    def too_many_requests(e):
        return ("<h1>Too many requests</h1><p>Please wait a few minutes and try again.</p>", 429)

    @app.errorhandler(403)
    def forbidden(e):
        return ("<h1>Access denied</h1><p>You do not have permission to view this page.</p>", 403)

    # ─── TEMPLATE FILTERS & GLOBALS ────────────────────────
    @app.template_filter("img_url")
    def img_url(path):
        if not path:
            return ""
        if str(path).startswith(("http://", "https://")):
            return path
        from flask import url_for
        return url_for("static", filename=path)

    @app.template_global()
    def site_img(name, ext="jpg"):
        """Return URL to a site identity image, with SVG fallback."""
        import os
        static_dir = current_app.static_folder
        for candidate_ext in [ext, "jpg", "jpeg", "png", "webp"]:
            path = os.path.join(static_dir, "img", "site", f"{name}.{candidate_ext}")
            if os.path.exists(path):
                from flask import url_for
                return url_for("static", filename=f"img/site/{name}.{candidate_ext}")
        from flask import url_for
        return url_for("static", filename=f"img/{name}.svg")

    # ─── SECURITY HEADERS ──────────────────────────────────
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://player.vimeo.com https://maps.google.com https://www.google.com; "
            "connect-src 'self'; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "object-src 'none';"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        if is_prod and request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Do not let browsers/proxies cache logged-in pages (shared computers, cyber cafes)
        if request.endpoint != "static" and current_user.is_authenticated:
            response.headers["Cache-Control"] = "private, no-store"
        return response

    # ─── FORCE HTTPS IN PRODUCTION ─────────────────────────
    @app.before_request
    def force_https():
        from flask import redirect
        if is_prod and request.path != "/health" and not request.is_secure:
            return redirect(request.url.replace("http://", "https://", 1), code=301)

    @app.before_request
    def check_host():
        allowed = app.config.get("ALLOWED_HOSTS")
        if is_prod and allowed and request.path != "/health":
            if request.host.split(":")[0].lower() not in allowed:
                abort(400)

    # ─── RATE LIMITING ─────────────────────────────────────
    from .extensions import limiter
    if limiter:
        limiter.init_app(app)

        @limiter.request_filter
        def _skip_limits():
            # Static files, health checks and the payment webhook must never be throttled
            return request.endpoint in ("static", "main.health", "main.favicon",
                                        "main.robots", "shop.paystack_webhook")

    return app