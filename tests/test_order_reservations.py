from datetime import datetime, timedelta
from decimal import Decimal

from app.blueprints.shop import release_stale_order_reservations, _record_order_payment
from app.extensions import db
from app.models import (
    InventoryTransaction,
    Order,
    OrderItem,
    PaymentTransaction,
    Product,
)


def test_stale_order_reservation_is_released_once(app):
    with app.app_context():
        product = Product(name="Test toolkit", slug="test-toolkit", price=Decimal("10.00"), stock=8)
        db.session.add(product)
        db.session.flush()
        order = Order(
            total=Decimal("20.00"),
            status="pending",
            payment_status="unpaid",
            reference="MN-STALE123",
            created_at=datetime.utcnow() - timedelta(hours=3),
        )
        db.session.add(order)
        db.session.flush()
        db.session.add(OrderItem(order_id=order.id, product_id=product.id, qty=2, unit_price=product.price))
        db.session.add(InventoryTransaction(
            product_id=product.id, order_id=order.id, transaction_type="reservation",
            quantity=-2, reason="test reservation"
        ))
        db.session.commit()

        assert release_stale_order_reservations(minutes=60) == 1
        db.session.refresh(product)
        db.session.refresh(order)
        assert product.stock == 10
        assert order.status == "cancelled"
        assert order.payment_status == "expired"

        assert release_stale_order_reservations(minutes=60) == 0
        db.session.refresh(product)
        assert product.stock == 10
        assert InventoryTransaction.query.filter_by(
            order_id=order.id, transaction_type="reservation_release"
        ).count() == 1


def test_verified_order_payment_is_idempotent(app):
    with app.app_context():
        app.config["PAYSTACK_CURRENCY"] = "GHS"
        product = Product(name="Test adapter", slug="test-adapter", price=Decimal("15.00"), stock=3)
        db.session.add(product)
        db.session.flush()
        order = Order(
            total=Decimal("15.00"), status="pending", payment_status="initiated",
            reference="MN-PAID1234",
        )
        db.session.add(order)
        db.session.commit()

        payload = {
            "status": "success",
            "reference": order.reference,
            "amount": 1500,
            "currency": "GHS",
        }
        assert _record_order_payment(order.id, payload) == "paid"
        assert _record_order_payment(order.id, payload) == "paid"
        db.session.refresh(order)
        assert order.status == "paid"
        assert order.payment_status == "paid"
        assert PaymentTransaction.query.filter_by(provider_reference=order.reference).count() == 1
