from decimal import Decimal

from app.payments import payment_matches, to_minor


def test_to_minor_avoids_float_rounding(app):
    assert to_minor(Decimal("12.34")) == 1234
    assert to_minor("0.10") == 10


def test_payment_match_requires_success_reference_amount_and_currency(app):
    with app.app_context():
        app.config["ENV_NAME"] = "testing"
        app.config["PAYSTACK_CURRENCY"] = "GHS"
        data = {"status": "success", "reference": "MN-TEST1234", "amount": 1234, "currency": "GHS"}
        assert payment_matches(data, "MN-TEST1234", 1234)
        assert not payment_matches({**data, "reference": "wrong"}, "MN-TEST1234", 1234)
        assert not payment_matches({**data, "amount": 1235}, "MN-TEST1234", 1234)
        assert not payment_matches({**data, "currency": "NGN"}, "MN-TEST1234", 1234)
        assert not payment_matches({**data, "status": "failed"}, "MN-TEST1234", 1234)


def test_production_payment_fails_closed_without_configured_currency(app):
    with app.app_context():
        app.config["ENV_NAME"] = "production"
        app.config["PAYSTACK_CURRENCY"] = ""
        data = {"status": "success", "reference": "MN-TEST1234", "amount": 1234, "currency": "GHS"}
        assert not payment_matches(data, "MN-TEST1234", 1234)
