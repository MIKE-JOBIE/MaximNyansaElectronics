from flask import Blueprint, render_template, redirect, url_for, flash
from ...models import Donation
from ...forms import DonationForm
from ...extensions import db
from ...utils import gen_ref

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