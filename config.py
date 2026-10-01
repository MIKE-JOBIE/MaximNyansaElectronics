import os
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024

    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@maximnyansa.com")

    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@maximnyansa.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ChangeMe123!")

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

    # Secure session cookies — HTTPS only, no JS access, strict same-site
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 days

    # Content Security
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB upload cap
    WTF_CSRF_TIME_LIMIT = 60 * 60  # CSRF token valid 1 hour

    # Trust proxy headers from Render/Heroku/etc.
    PREFERRED_URL_SCHEME = "https"


class DevelopmentConfig(Config):
    DEBUG = True
    # Keep cookies working over http://localhost
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False