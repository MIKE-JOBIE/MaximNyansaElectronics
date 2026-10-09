"""Security / business-rule regression tests. Run with:  pytest -q"""
import hashlib
import hmac
import io
import json

import pytest
from werkzeug.datastructures import FileStorage

from app import create_app
from app.extensions import db
from app.models import User, Category, Product, Order, Program, Application
from app.utils import save_upload
from config import ProductionConfig

PW = "correct-horse-battery"


def make_user(email="a@example.com", pw=PW, role="trainee"):
    u = User(email=email, first_name="Ada", last_name="Test", role=role)
    u.set_password(pw)
    db.session.add(u)
    db.session.commit()
    return u


def login(client, email="a@example.com", pw=PW, nxt=""):
    return client.post("/auth/login" + nxt, data={"email": email, "password": pw, "remember": "no"})


def make_product(stock=1, active=True):
    c = Category(name="Laptops", slug="laptops")
    db.session.add(c)
    db.session.flush()
    p = Product(name="Test Laptop", slug="test-laptop", price=100, stock=stock,
                is_active=active, category_id=c.id)
    db.session.add(p)
    db.session.commit()
    return p


def test_security_headers(client):
    r = client.get("/")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert "object-src 'none'" in r.headers["Content-Security-Policy"]


def test_open_redirect_is_blocked(client):
    make_user()
    r = login(client, nxt="?next=//evil.example.com")
    assert r.status_code == 302
    assert "evil.example.com" not in r.headers["Location"]


def test_weak_password_rejected(client):
    r = client.post("/auth/register", data={
        "first_name": "A", "last_name": "B", "email": "weak@example.com",
        "password": "12345678901", "confirm": "12345678901"})
    assert r.status_code == 200
    assert User.query.filter_by(email="weak@example.com").first() is None


def test_password_change_signs_out_old_sessions(app, client):
    u = make_user()
    login(client)
    assert client.get("/auth/profile").status_code == 200
    u.set_password("a-brand-new-passphrase")
    db.session.commit()
    assert client.get("/auth/profile").status_code == 302   # old session no longer valid


def test_cart_never_exceeds_stock(app, client):
    p = make_product(stock=1)
    client.post(f"/shop/cart/add/{p.id}")
    client.post(f"/shop/cart/add/{p.id}")
    with client.session_transaction() as s:
        assert s["cart"][str(p.id)] == 1


def test_inactive_product_cannot_be_added(app, client):
    p = make_product(active=False)
    assert client.post(f"/shop/cart/add/{p.id}").status_code == 404


def _signed(payload, key):
    body = json.dumps(payload).encode()
    return body, hmac.new(key.encode(), body, hashlib.sha512).hexdigest()


def _order(total=25):
    u = make_user()
    o = Order(user_id=u.id, total=total, status="pending", reference="MN-TEST0001",
              full_name="Ada", phone="1", address="x", payment_status="unpaid")
    db.session.add(o)
    db.session.commit()
    return o


def test_webhook_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", "sk_test_dummy")
    r = client.post("/shop/webhook/paystack", data=b"{}", headers={"x-paystack-signature": "bad"})
    assert r.status_code == 401


def test_webhook_marks_order_paid_only_when_amount_matches(app, client, monkeypatch):
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", "sk_test_dummy")
    o = _order(total=25)
    wrong = {"event": "charge.success", "data": {"status": "success", "reference": o.reference, "amount": 100, "currency": "NGN"}}
    body, sig = _signed(wrong, "sk_test_dummy")
    assert client.post("/shop/webhook/paystack", data=body, headers={"x-paystack-signature": sig}).status_code == 200
    db.session.refresh(o)
    assert o.payment_status != "paid"            # underpayment is NOT accepted

    right = {"event": "charge.success", "data": {"status": "success", "reference": o.reference, "amount": 2500, "currency": "NGN"}}
    body, sig = _signed(right, "sk_test_dummy")
    client.post("/shop/webhook/paystack", data=body, headers={"x-paystack-signature": sig})
    db.session.refresh(o)
    assert o.payment_status == "paid"


def test_apply_to_closed_program_is_rejected(app, client):
    make_user()
    login(client)
    closed = Program(title="Closed", slug="closed", status="closed", capacity=5, summary="s", description="d")
    db.session.add(closed)
    db.session.commit()
    client.post("/training/apply", data={"program_id": closed.id, "motivation": "I want to learn electronics repair properly",
                                      "education": "Secondary school", "address": "Freetown", "phone": "07600000"})
    assert Application.query.count() == 0


def test_non_admin_cannot_open_admin(client):
    make_user()
    login(client)
    assert client.get("/admin/").status_code in (403, 302)


def test_upload_rejects_non_images(app):
    with app.test_request_context():
        fake = FileStorage(stream=io.BytesIO(b"<html><script>alert(1)</script></html>"), filename="x.html")
        assert save_upload(fake, "t_", preset="news") is None
        doc = FileStorage(stream=io.BytesIO(b"<svg onload=alert(1)>"), filename="x.svg")
        assert save_upload(doc, "t_", kind="document") is None


def test_production_refuses_weak_secret():
    class Weak(ProductionConfig):
        SECRET_KEY = "change-me"
    with pytest.raises(RuntimeError):
        create_app(Weak)
