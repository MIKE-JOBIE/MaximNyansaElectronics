from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(20), default="trainee")
    first_name    = db.Column(db.String(80))
    last_name     = db.Column(db.String(80))
    phone         = db.Column(db.String(40))
    address       = db.Column(db.String(255))
    is_active_flag= db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    applications  = db.relationship("Application", backref="applicant", lazy="dynamic", cascade="all, delete-orphan")
    orders        = db.relationship("Order", backref="customer", lazy="dynamic")

    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)
    @property
    def full_name(self): return f"{self.first_name or ''} {self.last_name or ''}".strip() or self.email
    @property
    def is_admin(self): return self.role == "admin"
    @property
    def is_active(self): return self.is_active_flag

class Program(db.Model):
    __tablename__ = "programs"
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    slug        = db.Column(db.String(220), unique=True, index=True)
    summary     = db.Column(db.String(300))
    description = db.Column(db.Text)
    start_date  = db.Column(db.Date)
    end_date    = db.Column(db.Date)
    capacity    = db.Column(db.Integer, default=20)
    fee         = db.Column(db.Numeric(10, 2), default=0)
    status      = db.Column(db.String(20), default="open")
    cover_image = db.Column(db.String(255))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    applications = db.relationship("Application", backref="program", lazy="dynamic")

class Application(db.Model):
    __tablename__ = "applications"
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    program_id     = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=False)
    motivation     = db.Column(db.Text)
    education      = db.Column(db.String(200))
    address        = db.Column(db.String(255))
    phone          = db.Column(db.String(40))
    status         = db.Column(db.String(20), default="pending")
    submitted_at   = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at    = db.Column(db.DateTime)
    reviewer_notes = db.Column(db.Text)

class Category(db.Model):
    __tablename__ = "categories"
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    slug = db.Column(db.String(120), unique=True)
    products = db.relationship("Product", backref="category", lazy="dynamic")

class Product(db.Model):
    __tablename__ = "products"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    slug        = db.Column(db.String(220), unique=True, index=True)
    description = db.Column(db.Text)
    price       = db.Column(db.Numeric(10, 2), nullable=False)
    stock       = db.Column(db.Integer, default=0)
    condition   = db.Column(db.String(20), default="new")
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    image       = db.Column(db.String(255))
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    __tablename__ = "orders"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"))
    total      = db.Column(db.Numeric(10, 2), default=0)
    status     = db.Column(db.String(20), default="pending")
    reference  = db.Column(db.String(40), unique=True)
    full_name  = db.Column(db.String(120))
    phone      = db.Column(db.String(40))
    address    = db.Column(db.String(255))
    notes      = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items      = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")

class OrderItem(db.Model):
    __tablename__ = "order_items"
    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey("orders.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    qty        = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2))
    product    = db.relationship("Product")

class Resource(db.Model):
    __tablename__ = "resources"
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200))
    slug        = db.Column(db.String(220), unique=True)
    description = db.Column(db.Text)
    file_url    = db.Column(db.String(400))
    category    = db.Column(db.String(80))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class Donation(db.Model):
    __tablename__ = "donations"
    id          = db.Column(db.Integer, primary_key=True)
    donor_name  = db.Column(db.String(120))
    email       = db.Column(db.String(120))
    amount      = db.Column(db.Numeric(10, 2))
    currency    = db.Column(db.String(5), default="USD")
    message     = db.Column(db.Text)
    reference   = db.Column(db.String(60))
    verified    = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    __tablename__ = "posts"
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200))
    slug        = db.Column(db.String(220), unique=True)
    body        = db.Column(db.Text)
    cover_image = db.Column(db.String(255))
    published_at= db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    __tablename__ = "messages"
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120))
    email      = db.Column(db.String(120))
    subject    = db.Column(db.String(200))
    body       = db.Column(db.Text)
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token      = db.Column(db.String(80), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used       = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="reset_tokens")

    @property
    def is_valid(self):
        return (not self.used) and self.expires_at > datetime.utcnow()
    
class SiteSetting(db.Model):
    __tablename__ = "site_settings"
    id         = db.Column(db.Integer, primary_key=True)
    key        = db.Column(db.String(80), unique=True, nullable=False, index=True)
    value      = db.Column(db.Text, default="")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get(key, default=""):
        s = SiteSetting.query.filter_by(key=key).first()
        return s.value if s else default

    @staticmethod
    def set(key, value):
        s = SiteSetting.query.filter_by(key=key).first()
        if s:
            s.value = str(value)
        else:
            db.session.add(SiteSetting(key=key, value=str(value)))
        db.session.commit()

    @staticmethod
    def all_dict():
        return {s.key: s.value for s in SiteSetting.query.all()}