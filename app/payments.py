import os
import requests
from flask import current_app


PAYSTACK_BASE = "https://api.paystack.co"


def _secret_key():
    return os.getenv("PAYSTACK_SECRET_KEY", "")


def is_configured():
    """True if Paystack secret key is set."""
    return bool(_secret_key())


def initialize_transaction(email, amount_minor, reference, callback_url, metadata=None):
    """
    Initialize a Paystack payment.
    amount_minor: amount in the smallest currency unit (e.g., cents/kobo).
                  For SLE, Paystack may require amounts in SLE units — check docs.
    Returns dict with 'authorization_url' and 'access_code', or None on failure.
    """
    if not is_configured():
        current_app.logger.warning("Paystack not configured; skipping initialize.")
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
        r.raise_for_status()
        return r.json().get("data")
    except Exception as e:
        current_app.logger.error(f"Paystack init failed: {e}")
        return None


def verify_transaction(reference):
    """Verify a transaction by reference. Returns dict with 'status' and 'amount'."""
    if not is_configured():
        return None
    try:
        r = requests.get(
            f"{PAYSTACK_BASE}/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {_secret_key()}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("data")
    except Exception as e:
        current_app.logger.error(f"Paystack verify failed: {e}")
        return None