from datetime import datetime, timedelta
from decimal import Decimal

from flask import (Blueprint, render_template, redirect, url_for, flash, session,
                   request, current_app, abort)
from flask_login import login_required, current_user

from ...models import (Product, Category, Order, OrderItem, Donation,
                        InventoryTransaction, PaymentTransaction)
from ...forms import CheckoutForm
from ...extensions import db, csrf
from ...utils import gen_ref, external_url
from ...payments import (is_configured as paystack_ready, initialize_transaction,
                         verify_transaction, verify_signature, payment_matches, to_minor)


shop_bp = Blueprint("shop", __name__, template_folder="../../templates/shop")

MAX_QTY_PER_LINE = 10


def _cart():
    return session.setdefault("cart", {})


def cart_count():
    """Return the total number of items in the session cart."""
    cart = session.get("cart", {})
    return sum(cart.values())


def _cart_lines():
    """Cart contents as (items, total). Drops products that no longer exist or are inactive."""
    cart = _cart()
    ids = [int(k) for k in cart if str(k).isdigit()]
    products = {}
    if ids:
        products = {p.id: p for p in Product.query.filter(Product.id.in_(ids), Product.is_active.is_(True)).all()}
    items, total, dirty = [], Decimal("0.00"), False
    for pid, qty in list(cart.items()):
        p = products.get(int(pid)) if str(pid).isdigit() else None
        if p is None:
            cart.pop(pid, None)
            dirty = True
            continue
        qty = max(1, min(int(qty), MAX_QTY_PER_LINE))
        line = Decimal(p.price) * qty
        items.append({"product": p, "qty": qty, "line": line})
        total += line
    if dirty:
        session.modified = True
    return items, total


def restore_order_stock(order, reason="Order reservation released"):
    """Restore an order's reserved stock once; caller should hold the order row lock."""
    if order.status == "paid":
        return 0
    already_released = InventoryTransaction.query.filter_by(
        order_id=order.id, transaction_type="reservation_release"
    ).first()
    if already_released:
        return 0

    product_ids = [it.product_id for it in order.items if it.product_id]
    locked = {}
    if product_ids:
        locked = {p.id: p for p in Product.query.filter(
            Product.id.in_(product_ids)
        ).with_for_update().all()}

    restored = 0
    for item in order.items:
        product = locked.get(item.product_id)
        qty = max(0, int(item.qty or 0))
        if product is None or qty == 0:
            continue
        product.stock = (product.stock or 0) + qty
        db.session.add(InventoryTransaction(
            product_id=product.id,
            order_id=order.id,
            actor_user_id=None,
            transaction_type="reservation_release",
            quantity=qty,
            reason=str(reason)[:255],
        ))
        restored += qty
    return restored


def release_stale_order_reservations(minutes=60, limit=100):
    """Cancel stale unpaid orders and restore their stock in one DB transaction."""
    cutoff = datetime.utcnow() - timedelta(minutes=max(1, int(minutes)))
    orders = (Order.query
              .filter(Order.status == "pending",
                      Order.payment_status.in_(("unpaid", "initiated", "failed")),
                      Order.created_at <= cutoff)
              .order_by(Order.created_at.asc())
              .with_for_update(skip_locked=True)
              .limit(max(1, min(int(limit), 500))).all())
    released = 0
    for order in orders:
        # The row lock serializes this with payment callbacks/webhooks.
        if order.status != "pending" or order.payment_status == "paid":
            continue
        restore_order_stock(order, "Expired unpaid order reservation")
        order.status = "cancelled"
        order.payment_status = "expired"
        released += 1
    db.session.commit()
    return released


def _record_order_payment(order_id, data, event_id=None):
    """Record a verified payment once; late payments after stock release need manual review."""
    order = Order.query.filter_by(id=order_id).with_for_update().first()
    if order is None:
        return "missing"
    if order.payment_status == "paid":
        return "paid"

    matches = payment_matches(data, order.reference, to_minor(order.total))
    if not matches:
        if data and data.get("status") == "success":
            existing_review = PaymentTransaction.query.filter_by(
                provider_reference=order.reference
            ).first()
            if not existing_review and data.get("reference") == order.reference:
                try:
                    db.session.add(PaymentTransaction(
                        order_id=order.id,
                        provider="paystack",
                        provider_reference=order.reference,
                        amount=(Decimal(str(data["amount"])) / Decimal("100")),
                        currency=str(data.get("currency", "")).upper()[:5],
                        status="review",
                        verified_at=datetime.utcnow(),
                    ))
                except Exception:
                    db.session.rollback()
                    current_app.logger.exception("Could not record payment review for order %s", order.reference)
                    return "review"
            order.payment_status = "review"
            db.session.commit()
            return "review"
        return "failed"

    existing = PaymentTransaction.query.filter_by(
        provider_reference=order.reference
    ).first()
    if existing:
        if existing.order_id == order.id and existing.status == "success":
            order.payment_status = "paid"
            order.status = "paid"
            db.session.commit()
            return "paid"
        order.payment_status = "review"
        db.session.commit()
        return "review"

    if event_id:
        duplicate_event = PaymentTransaction.query.filter_by(event_id=event_id).first()
        if duplicate_event and duplicate_event.provider_reference != order.reference:
            order.payment_status = "review"
            db.session.commit()
            return "review"

    if order.status == "cancelled":
        order.payment_status = "review"
        db.session.add(PaymentTransaction(
            order_id=order.id,
            provider="paystack",
            provider_reference=order.reference,
            amount=(Decimal(str(data["amount"])) / Decimal("100")),
            currency=str(data.get("currency", "")).upper()[:5],
            status="review",
            event_id=event_id,
            verified_at=datetime.utcnow(),
        ))
        db.session.commit()
        return "review"

    db.session.add(PaymentTransaction(
        order_id=order.id,
        provider="paystack",
        provider_reference=order.reference,
        amount=(Decimal(str(data["amount"])) / Decimal("100")),
        currency=str(data.get("currency", "")).upper()[:5],
        status="success",
        event_id=event_id,
        verified_at=datetime.utcnow(),
    ))
    order.payment_status = "paid"
    order.status = "paid"
    db.session.commit()
    return "paid"


def _record_donation_payment(donation, data, event_id=None):
    """Record a verified donation payment once."""
    locked = Donation.query.filter_by(id=donation.id).with_for_update().first()
    if locked is None:
        return "missing"
    if locked.payment_status == "paid":
        return "paid"
    matches = payment_matches(data, locked.reference, to_minor(locked.amount))
    if not matches:
        if data and data.get("status") == "success":
            existing_review = PaymentTransaction.query.filter_by(
                provider_reference=locked.reference
            ).first()
            if not existing_review and data.get("reference") == locked.reference:
                db.session.add(PaymentTransaction(
                    donation_id=locked.id,
                    provider="paystack",
                    provider_reference=locked.reference,
                    amount=(Decimal(str(data["amount"])) / Decimal("100")),
                    currency=str(data.get("currency", "")).upper()[:5],
                    status="review",
                    verified_at=datetime.utcnow(),
                ))
            locked.payment_status = "review"
            db.session.commit()
            return "review"
        return "failed"

    existing = PaymentTransaction.query.filter_by(provider_reference=locked.reference).first()
    if existing:
        if existing.donation_id == locked.id and existing.status == "success":
            locked.payment_status = "paid"
            locked.verified = True
            db.session.commit()
            return "paid"
        locked.payment_status = "review"
        db.session.commit()
        return "review"

    if event_id and PaymentTransaction.query.filter_by(event_id=event_id).first():
        locked.payment_status = "review"
        db.session.commit()
        return "review"

    db.session.add(PaymentTransaction(
        donation_id=locked.id,
        provider="paystack",
        provider_reference=locked.reference,
        amount=(Decimal(str(data["amount"])) / Decimal("100")),
        currency=str(data.get("currency", "")).upper()[:5],
        status="success",
        event_id=event_id,
        verified_at=datetime.utcnow(),
    ))
    locked.payment_status = "paid"
    locked.verified = True
    db.session.commit()
    return "paid"


@shop_bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    cat_slug = request.args.get("cat")
    q = request.args.get("q", "").strip()[:80]
    condition = request.args.get("condition", "")
    sort = request.args.get("sort", "newest")

    query = Product.query.filter_by(is_active=True)

    if cat_slug:
        c = Category.query.filter_by(slug=cat_slug).first()
        if c:
            query = query.filter_by(category_id=c.id)
    if q:
        like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.filter(Product.name.ilike(like, escape="\\"))
    if condition in ("new", "refurbished", "used"):
        query = query.filter_by(condition=condition)

    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "name":
        query = query.order_by(Product.name.asc())
    else:
        query = query.order_by(Product.created_at.desc())

    pagination = query.paginate(page=page, per_page=9, error_out=False)
    categories = Category.query.all()

    return render_template("shop/index.html",
                           products=pagination.items,
                           pagination=pagination,
                           categories=categories,
                           current_cat=cat_slug,
                           q=q,
                           condition=condition,
                           sort=sort)


@shop_bp.route("/product/<slug>")
def product_detail(slug):
    p = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
    return render_template("shop/product.html", product=p)


@shop_bp.route("/cart/add/<int:pid>", methods=["POST"])
def add_to_cart(pid):
    p = Product.query.filter_by(id=pid, is_active=True).first_or_404()
    if (p.stock or 0) <= 0:
        flash(f"Sorry, {p.name} is out of stock.", "warning")
        return redirect(url_for("shop.product_detail", slug=p.slug))
    cart = _cart()
    cart[str(pid)] = min(cart.get(str(pid), 0) + 1, MAX_QTY_PER_LINE, p.stock)
    session.modified = True
    flash(f"{p.name} added to cart", "success")
    return redirect(url_for("shop.cart_view"))


@shop_bp.route("/cart")
def cart_view():
    items, total = _cart_lines()
    return render_template("shop/cart.html", items=items, total=total)


@shop_bp.route("/cart/update/<int:pid>", methods=["POST"])
def cart_update(pid):
    qty = max(0, min(request.form.get("qty", type=int) or 0, MAX_QTY_PER_LINE))
    cart = _cart()
    if qty == 0:
        cart.pop(str(pid), None)
    else:
        cart[str(pid)] = qty
    session.modified = True
    return redirect(url_for("shop.cart_view"))


@shop_bp.route("/cart/remove/<int:pid>", methods=["POST"])
def cart_remove(pid):
    _cart().pop(str(pid), None)
    session.modified = True
    return redirect(url_for("shop.cart_view"))


@shop_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    if not _cart():
        flash("Your cart is empty.", "info")
        return redirect(url_for("shop.index"))
    form = CheckoutForm()
    items, total = _cart_lines()
    if not items:
        flash("Your cart is empty.", "info")
        return redirect(url_for("shop.index"))
    if form.validate_on_submit():
        # Lock the product rows so two buyers cannot take the last unit at the same time
        ids = [it["product"].id for it in items]
        locked = {p.id: p for p in Product.query.filter(Product.id.in_(ids)).with_for_update().all()}
        order_total = Decimal("0.00")
        for it in items:
            p = locked[it["product"].id]
            if not p.is_active or (p.stock or 0) < it["qty"]:
                db.session.rollback()
                flash(f"Sorry, only {max(p.stock or 0, 0)} of {p.name} left. Please update your cart.", "warning")
                return redirect(url_for("shop.cart_view"))
            order_total += Decimal(p.price) * it["qty"]
        order = Order(user_id=current_user.id, total=order_total, status="pending",
                      reference=gen_ref("MN"), full_name=form.full_name.data,
                      phone=form.phone.data, address=form.address.data, notes=form.notes.data)
        db.session.add(order)
        db.session.flush()
        for it in items:
            p = locked[it["product"].id]
            db.session.add(OrderItem(order_id=order.id, product_id=p.id, qty=it["qty"], unit_price=p.price))
            p.stock -= it["qty"]
            db.session.add(InventoryTransaction(
                product_id=p.id,
                order_id=order.id,
                actor_user_id=current_user.id,
                transaction_type="reservation",
                quantity=-int(it["qty"]),
                reason="Stock reserved for checkout",
            ))
        db.session.commit()
        session["cart"] = {}
        session.modified = True
        flash(f"Order {order.reference} placed!", "success")
        return redirect(url_for("shop.order_success", ref=order.reference))
    return render_template("shop/checkout.html", form=form, items=items, total=total)


@shop_bp.route("/order/<ref>")
@login_required
def order_success(ref):
    o = Order.query.filter_by(reference=ref, user_id=current_user.id).first_or_404()
    return render_template("shop/order_success.html", order=o)


@shop_bp.route("/orders")
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id)\
        .order_by(Order.created_at.desc()).limit(200).all()
    return render_template("shop/my_orders.html", orders=orders)


@shop_bp.route("/orders/<ref>")
@login_required
def order_detail(ref):
    o = Order.query.filter_by(reference=ref, user_id=current_user.id).first_or_404()
    return render_template("shop/order_detail.html", order=o)


@shop_bp.route("/pay/<ref>")
@login_required
def pay(ref):
    """Start a Paystack payment for an order."""
    o = Order.query.filter_by(reference=ref, user_id=current_user.id).first_or_404()

    if o.payment_status == "paid":
        flash("This order is already paid.", "info")
        return redirect(url_for("shop.order_detail", ref=o.reference))
    if o.payment_status == "review":
        flash("This payment needs manual review. Please contact our team before trying again.", "warning")
        return redirect(url_for("shop.order_detail", ref=o.reference))
    if o.status == "cancelled":
        flash("This order was cancelled. Please place a new order.", "warning")
        return redirect(url_for("shop.order_detail", ref=o.reference))

    if not paystack_ready():
        return render_template("shop/pay_manual.html", order=o)

    try:
        callback = external_url("shop.pay_callback", ref=o.reference)
        data = initialize_transaction(
            email=current_user.email,
            amount_minor=to_minor(o.total),
            reference=o.reference,
            callback_url=callback,
            metadata={
                "type": "order",
                "order_id": o.id,
                "user_id": current_user.id,
                "custom_fields": [
                    {"display_name": "Order Reference", "variable_name": "order_ref", "value": o.reference},
                ],
            },
        )
    except Exception as e:
        current_app.logger.exception(f"Paystack init failed for {o.reference}: {e}")
        flash("Could not start payment. Please try again or contact us.", "danger")
        return render_template("shop/pay_manual.html", order=o)

    if not data or not data.get("authorization_url"):
        current_app.logger.error(f"Paystack returned no auth URL for {o.reference}")
        flash("Payment provider unavailable. Please use manual payment.", "warning")
        return render_template("shop/pay_manual.html", order=o)

    o.payment_ref = o.reference
    o.payment_status = "initiated"
    db.session.commit()

    return redirect(data["authorization_url"])


@shop_bp.route("/pay/callback/<ref>")
@login_required
def pay_callback(ref):
    order = Order.query.filter_by(reference=ref, user_id=current_user.id).first_or_404()
    data = verify_transaction(ref)
    if not data:
        flash("Payment status could not be verified yet. Please refresh your order later.", "warning")
        return redirect(url_for("shop.order_detail", ref=order.reference))

    if data.get("status") == "success":
        result = _record_order_payment(order.id, data)
        if result == "paid":
            flash(f"Payment received! Order {order.reference} confirmed.", "success")
        elif result == "review":
            current_app.logger.error("Payment for order %s requires manual review", order.reference)
            flash("Payment needs manual review. Please contact our team before paying again.", "warning")
        else:
            flash("Payment details did not match this order. Please contact our team.", "warning")
    else:
        locked = Order.query.filter_by(id=order.id).with_for_update().first()
        if locked and locked.payment_status != "paid" and locked.status != "cancelled":
            locked.payment_status = "failed"
            db.session.commit()
        flash("Payment was not completed. Your reservation will expire automatically if unpaid.", "warning")
    return redirect(url_for("shop.order_detail", ref=order.reference))


@shop_bp.route("/webhook/paystack", methods=["POST"])
@csrf.exempt
def paystack_webhook():
    """Verify signed Paystack events against Paystack's transaction verification API."""
    if not verify_signature(request.get_data(), request.headers.get("x-paystack-signature", "")):
        abort(401)
    event = request.get_json(silent=True) or {}
    if event.get("event") != "charge.success":
        return "", 200

    event_data = event.get("data") or {}
    ref = str(event_data.get("reference", "")).strip()
    if not ref:
        return "", 400

    # Verify with Paystack's API instead of trusting the webhook payload alone.
    verified = verify_transaction(ref)
    if not verified:
        current_app.logger.warning("Paystack verification temporarily unavailable for reference %s", ref)
        return "", 503

    event_id = str(event.get("id")) if event.get("id") is not None else None
    order = Order.query.filter_by(reference=ref).first()
    if order is not None:
        result = _record_order_payment(order.id, verified, event_id=event_id)
        if result == "review":
            current_app.logger.error("Paystack order payment requires review: %s", ref)
        return "", 200

    donation = Donation.query.filter_by(reference=ref).first()
    if donation is not None:
        result = _record_donation_payment(donation, verified, event_id=event_id)
        if result == "review":
            current_app.logger.error("Paystack donation payment requires review: %s", ref)
        return "", 200

    current_app.logger.warning("Verified Paystack payment has no matching order/donation: %s", ref)
    return "", 200
