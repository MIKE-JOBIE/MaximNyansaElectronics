from decimal import Decimal

from flask import (Blueprint, render_template, redirect, url_for, flash, session,
                   request, current_app, abort)
from flask_login import login_required, current_user

from ...models import Product, Category, Order, OrderItem, Donation
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


def restore_order_stock(order):
    """Put reserved stock back; caller must hold the order row lock."""
    product_ids = [it.product_id for it in order.items if it.product_id]
    if product_ids:
        locked = {p.id: p for p in Product.query.filter(Product.id.in_(product_ids)).with_for_update().all()}
        for it in order.items:
            product = locked.get(it.product_id)
            if product is not None:
                product.stock = (product.stock or 0) + (it.qty or 0)


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
            p.stock -= it["qty"]          # reserved; restored if the order is cancelled
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
    o = Order.query.filter_by(reference=ref, user_id=current_user.id).first_or_404()
    if o.payment_status == "paid":
        return redirect(url_for("shop.order_detail", ref=o.reference))
    if o.status == "cancelled":
        flash("This order was cancelled and cannot be paid.", "warning")
        return redirect(url_for("shop.order_detail", ref=o.reference))
    data = verify_transaction(ref)
    if payment_matches(data, o.reference, to_minor(o.total)):
        o.payment_status = "paid"
        o.status = "paid"
        db.session.commit()
        flash(f"Payment received! Order {o.reference} confirmed.", "success")
    elif data and data.get("status") == "success":
        # Paid, but amount/currency do not match the order: needs a human to look at it
        current_app.logger.error("Payment mismatch for order %s: %s", o.reference,
                                 {k: data.get(k) for k in ("amount", "currency", "reference")})
        o.payment_status = "review"
        db.session.commit()
        flash("We received a payment that does not match this order. Our team will contact you.", "warning")
    else:
        o.payment_status = "failed"
        db.session.commit()
        flash("Payment failed or was cancelled. Your reserved stock remains available for a new order after the reservation is released.", "warning")
    return redirect(url_for("shop.order_detail", ref=o.reference))


@shop_bp.route("/webhook/paystack", methods=["POST"])
@csrf.exempt
def paystack_webhook():
    """
    Paystack server-to-server notification. Marks orders/donations paid even if the
    customer closed their browser before returning. Set this URL in the Paystack dashboard:
    https://<your-site>/shop/webhook/paystack
    """
    if not verify_signature(request.get_data(), request.headers.get("x-paystack-signature", "")):
        abort(401)
    event = request.get_json(silent=True) or {}
    if event.get("event") == "charge.success":
        data = event.get("data") or {}
        ref = str(data.get("reference", ""))
        order = Order.query.filter_by(reference=ref).first()
        if order is not None:
            if order.status != "cancelled" and order.payment_status != "paid" and payment_matches(data, ref, to_minor(order.total)):
                order.payment_status = "paid"
                order.status = "paid"
                db.session.commit()
        else:
            donation = Donation.query.filter_by(reference=ref).first()
            if donation is not None and donation.payment_status != "paid" \
                    and payment_matches(data, ref, to_minor(donation.amount)):
                donation.payment_status = "paid"
                donation.verified = True
                db.session.commit()
    return "", 200
