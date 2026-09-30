from flask import Blueprint, render_template, redirect, url_for, flash
from ...models import Donation
from ...forms import DonationForm
from ...extensions import db
from ...utils import gen_ref

from flask import current_app
from ...payments import is_configured as paystack_ready, initialize_transaction, verify_transaction

donors_bp = Blueprint("donors", __name__, template_folder="../../templates/donors")

@donors_bp.route("/", methods=["GET","POST"])
def index():
    form = DonationForm()
    if form.validate_on_submit():
        d = Donation(donor_name=form.donor_name.data, email=form.email.data,
                     amount=form.amount.data, currency=form.currency.data,
                     message=form.message.data, reference=gen_ref("DON"))
        db.session.add(d); db.session.commit()
        flash("Thank you! We'll follow up with payment instructions.", "success")
        return redirect(url_for("donors.index"))
    total = db.session.query(db.func.coalesce(db.func.sum(Donation.amount), 0)).scalar()
    donors_count = Donation.query.count()
    return render_template("donors/index.html", form=form, total=total, donors_count=donors_count)

@donors_bp.route("/pay/<int:did>")
def pay(did):
    d = Donation.query.get_or_404(did)
    if not paystack_ready():
        flash("Online donations not yet enabled. We'll contact you.", "info")
        return redirect(url_for("donors.index"))
    callback = url_for("donors.pay_callback", did=d.id, _external=True)
    amount_minor = int(float(d.amount) * 100)
    data = initialize_transaction(
        email=d.email,
        amount_minor=amount_minor,
        reference=d.reference or f"DON-{d.id}",
        callback_url=callback,
        metadata={"type": "donation", "donation_id": d.id},
    )
    if not data:
        flash("Could not start payment. Try again.", "danger")
        return redirect(url_for("donors.index"))
    d.payment_ref = d.reference or f"DON-{d.id}"
    db.session.commit()
    return redirect(data["authorization_url"])


@donors_bp.route("/pay/callback/<int:did>")
def pay_callback(did):
    d = Donation.query.get_or_404(did)
    ref = d.payment_ref or f"DON-{d.id}"
    data = verify_transaction(ref)
    if data and data.get("status") == "success":
        d.payment_status = "paid"
        d.verified = True
        db.session.commit()
        flash("Thank you! Your donation was received.", "success")
    else:
        d.payment_status = "failed"
        db.session.commit()
        flash("Payment failed.", "warning")
    return redirect(url_for("donors.index"))