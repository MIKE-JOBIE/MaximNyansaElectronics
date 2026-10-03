import os
from flask import Flask, render_template, current_app
from .extensions import db, migrate, login_manager, csrf, mail
from config import DevelopmentConfig, ProductionConfig, TestingConfig


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    if config_object:
        app.config.from_object(config_object)
    else:
        env = os.getenv("FLASK_ENV", "development")
        app.config.from_object(ProductionConfig if env == "production" else DevelopmentConfig)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

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

    from .models import User

    @login_manager.user_loader
    def load_user(uid):
        return User.query.get(int(uid))

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
            "brand_name":   site.get("brand_name", "Maxim Nyansa Electronics"),
            "brand_phone":  site.get("brand_phone", "+232 31 950 662"),
            "brand_email":  site.get("brand_email", "info@maximnyansa.com"),
            "brand_address":site.get("brand_address", "Freetown, Sierra Leone"),
            "brand_tagline":site.get("brand_tagline", "Skills Today, Success Tomorrow"),
            "site": site,
        }

    from .commands import register_commands
    register_commands(app)

    from .backup import register_backup_commands
    register_backup_commands(app)

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500
    
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
        """
        Return URL to a site identity image.
        - Looks for /static/img/site/{name}.{ext}
        - Tries .jpg, .jpeg, .png, .webp automatically
        - Falls back to /static/img/{name}.svg placeholder if none exist
        """
        import os
        static_dir = current_app.static_folder
        for candidate_ext in [ext, "jpg", "jpeg", "png", "webp"]:
            path = os.path.join(static_dir, "img", "site", f"{name}.{candidate_ext}")
            if os.path.exists(path):
                from flask import url_for
                return url_for("static", filename=f"img/site/{name}.{candidate_ext}")
        # Fallback to SVG placeholder
        from flask import url_for
        return url_for("static", filename=f"img/{name}.svg")
    
        # ─── SECURITY HEADERS ────────────────────────────────────
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # Content Security Policy — allows inline styles (needed for charts + brand colors)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "frame-ancestors 'self'; "
            "base-uri 'self';"
        )
        return response
    
        # ─── FORCE HTTPS IN PRODUCTION ───────────────────────────
    @app.before_request
    def force_https():
        from flask import request, redirect
        if app.config.get("ENV") == "production" or not app.debug:
            if request.headers.get("X-Forwarded-Proto", "http") == "http":
                url = request.url.replace("http://", "https://", 1)
                return redirect(url, code=301)
            

    # ─── RATE LIMITING ───────────────────────────────────────
    from .extensions import limiter
    if limiter:
        limiter.init_app(app)
            

    return app