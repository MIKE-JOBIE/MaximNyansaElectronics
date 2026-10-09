import hashlib
import hmac
import os
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import quote

import requests
from flask import current_app, url_for


PAYSTACK_BASE = "https://api.paystack.co"


def _secret_key():
    return os.getenv("PAYSTACK_SECRET_KEY", "").strip()


def is_configured():
    """True if Paystack is properly configured."""
    return bool(_secret_key())


def is_test_mode():
    """True if using test keys."""
    return os.getenv("PAYSTACK_TEST_MODE", "false").lower() == "true"


def to_minor(amount):
    """Convert a Decimal/float/str amount to Paystack minor units (x100) without float drift."""
    return int((Decimal(str(amount)) * 100).to_integral_value(rounding=ROUND_HALF_UP))


def verify_signature(raw_body, signature):
    """Check the x-paystack-signature header (HMAC-SHA512 of the raw body)."""
    key = _secret_key().encode()
    if not key or not signature:
        return False
    expected = hmac.new(key, raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


def payment_matches(data, reference, amount_minor):
    """True only if Paystack says success AND reference, amount and currency all match."""
    if not data or data.get("status") != "success":
        return False
    if data.get("reference") != reference:
        return False
    try:
        if int(data.get("amount", -1)) != int(amount_minor):
            return False
    except (TypeError, ValueError):
        return False
    currency = current_app.config.get("PAYSTACK_CURRENCY")
    if currency and str(data.get("currency", "")).upper() != currency:
        return False
    return True


def initialize_transaction(email, amount_minor, reference, callback_url, metadata=None):
    """
    Initialize a Paystack payment.
    amount_minor: amount in the smallest unit (e.g., kobo/cents).
    Returns dict with 'authorization_url' and 'access_code', or None on failure.
    """
    if not is_configured():
        current_app.logger.warning("Paystack not configured.")
        return None
    try:
        payload = {
            "email": email,
            "amount": int(amount_minor),
            "reference": reference,
            "callback_url": callback_url,
            "metadata": metadata or {},
        }
        r = requests.post(
            f"{PAYSTACK_BASE}/transaction/initialize",
            json=payload,
            headers={
                "Authorization": f"Bearer {_secret_key()}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        if r.status_code != 200:
            current_app.logger.error(f"Paystack init failed: {r.status_code} {r.text}")
            return None
        return r.json().get("data")
    except Exception as e:
        current_app.logger.error(f"Paystack init exception: {e}")
        return None


def verify_transaction(reference):
    """Verify a transaction by reference."""
    if not is_configured():
        return None
    try:
        r = requests.get(
            f"{PAYSTACK_BASE}/transaction/verify/{quote(str(reference), safe='')}",
            headers={"Authorization": f"Bearer {_secret_key()}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("data")
    except Exception as e:
        current_app.logger.error(f"Paystack verify failed: {e}")
        return None