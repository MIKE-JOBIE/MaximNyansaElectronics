from flask import Blueprint, render_template, redirect, url_for, flash, current_app

from ...models import Donation
from ...forms import DonationForm
from ...extensions import db, rate_limit
from ...utils import gen_ref, external_url
from ...payments import (is_configured as paystack_ready, initialize_transaction,
                         verify_transaction, payment_matches, to_minor)

donors_bp = Blueprint("donors", __name__, template_folder="../../templates/donors")


@donors_bp.route("/", methods=["GET", "POST"])
@rate_limit("10 per hour", methods=["POST"])
def index():
    form = DonationForm()
    if form.validate_on_submit():
        d = Donation(donor_name=form.donor_name.data, email=form.email.data,
                     amount=form.amount.data, currency=form.currency.data,
                     message=form.message.data, reference=gen_ref("DON"))
        db.session.add(d)
        db.session.commit()
        flash("Thank you! We'll follow up with payment instructions.", "success")
        return redirect(url_for("donors.index"))
    # Public totals only count donations that were actually received
    received = Donation.verified.is_(True)
    total = db.session.query(db.func.coalesce(db.func.sum(Donation.amount), 0)).filter(received).scalar()
    donors_count = Donation.query.filter(received).count()
    return render_template("donors/index.html", form=form, total=total, donors_count=donors_count)


# Donations are addressed by their random reference, not a guessable sequential id
@donors_bp.route("/pay/<ref>")
@rate_limit("20 per hour")
def pay(ref):
    d = Donation.query.filter_by(reference=ref).first_or_404()
    if d.payment_status == "paid":
        flash("This donation has already been received. Thank you!", "info")
        return redirect(url_for("donors.index"))
    if d.payment_status == "review":
        flash("This donation payment needs manual review. Please contact our team.", "warning")
        return redirect(url_for("donors.index"))
    if not paystack_ready():
        flash("Online donations not yet enabled. We'll contact you.", "info")
        return redirect(url_for("donors.index"))
    data = initialize_transaction(
        email=d.email,
        amount_minor=to_minor(d.amount),
        reference=d.reference,
        callback_url=external_url("donors.pay_callback", ref=d.reference),
        metadata={"type": "donation", "donation_id": d.id},
    )
    if not data or not data.get("authorization_url"):
        flash("Could not start payment. Try again.", "danger")
        return redirect(url_for("donors.index"))
    d.payment_ref = d.reference
    d.payment_status = "initiated"
    db.session.commit()
    return redirect(data["authorization_url"])


@donors_bp.route("/pay/callback/<ref>")
@rate_limit("30 per hour")
def pay_callback(ref):
    donation = Donation.query.filter_by(reference=ref).first_or_404()
    if donation.payment_status == "paid":
        return redirect(url_for("donors.index"))

    data = verify_transaction(donation.reference)
    if not data:
        flash("Payment status could not be verified yet. Please refresh later.", "warning")
        return redirect(url_for("donors.index"))

    if data.get("status") == "success":
        from ...blueprints.shop import _record_donation_payment
        result = _record_donation_payment(donation, data)
        if result == "paid":
            flash("Thank you! Your donation was received.", "success")
        elif result == "review":
            current_app.logger.error("Donation payment requires manual review: %s", donation.reference)
            flash("We received your payment and will confirm the details with you shortly.", "info")
        else:
            flash("Payment details did not match. Please contact our team.", "warning")
    else:
        if donation.payment_status != "paid":
            donation.payment_status = "failed"
            db.session.commit()
        flash("Payment was not completed.", "warning")
    return redirect(url_for("donors.index"))
