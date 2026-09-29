import os
from flask import Flask, render_template
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

    db.init_app(app); migrate.init_app(app, db)
    login_manager.init_app(app); csrf.init_app(app); mail.init_app(app)

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
    def load_user(uid): return User.query.get(int(uid))

    @app.context_processor
    def inject_globals():
        from datetime import datetime
        return {
            "current_year": datetime.utcnow().year,
            "brand_name": "Maxim Nyansa Electronics",
            "brand_phone": "+232 31 950 662",
            "brand_email": "info@maximnyansa.com",
            "brand_address": "5C BaiBureh Road, Ferry Junction, Freetown, Sierra Leone",
        }

    from .commands import register_commands
    register_commands(app)

        # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app