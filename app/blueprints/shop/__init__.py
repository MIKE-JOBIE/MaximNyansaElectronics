from flask import Blueprint, render_template, redirect, url_for, flash, session, request, current_app, abort
from flask_login import login_required, current_user
from ...models import Product, Category, Order, OrderItem
from ...forms import CheckoutForm
from ...extensions import db
from ...utils import gen_ref
from ...payments import is_configured as paystack_ready, initialize_transaction, verify_transaction


shop_bp = Blueprint("shop", __name__, template_folder="../../templates/shop")

def _cart(): return session.setdefault("cart", {})

def cart_count():
    """Return the total number of items in the session cart."""
    cart = session.get("cart", {})
    return sum(cart.values())

@shop_bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    cat_slug = request.args.get("cat")
    q = request.args.get("q", "").strip()
    condition = request.args.get("condition", "")
    sort = request.args.get("sort", "newest")

    query = Product.query.filter_by(is_active=True)

    if cat_slug:
        c = Category.query.filter_by(slug=cat_slug).first()
        if c:
            query = query.filter_by(category_id=c.id)
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
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
    p = Product.query.get_or_404(pid)
    cart = _cart()
    cart[str(pid)] = cart.get(str(pid), 0) + 1
    session.modified = True
    flash(f"✅ {p.name} added to cart", "success")

    # If the request came from a product detail page, go to cart
    # If the request came from the shop listing, stay on shop
    # In both cases, we go to the cart for clear feedback
    return redirect(url_for("shop.cart_view"))

@shop_bp.route("/cart")
def cart_view():
    cart = _cart()
    items, total = [], 0
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if p:
            line = float(p.price) * qty
            items.append({"product":p, "qty":qty, "line":line})
            total += line
    return render_template("shop/cart.html", items=items, total=total)

@shop_bp.route("/cart/update/<int:pid>", methods=["POST"])
def cart_update(pid):
    qty = max(0, request.form.get("qty", type=int) or 0)
    cart = _cart()
    if qty == 0: cart.pop(str(pid), None)
    else: cart[str(pid)] = qty
    session.modified = True
    return redirect(url_for("shop.cart_view"))

@shop_bp.route("/cart/remove/<int:pid>")
def cart_remove(pid):
    _cart().pop(str(pid), None); session.modified = True
    return redirect(url_for("shop.cart_view"))

@shop_bp.route("/checkout", methods=["GET","POST"])
@login_required
def checkout():
    cart = _cart()
    if not cart:
        flash("Your cart is empty.", "info"); return redirect(url_for("shop.index"))
    form = CheckoutForm()
    items, total = [], 0
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if p:
            line = float(p.price) * qty
            items.append({"product":p, "qty":qty, "line":line}); total += line
    if form.validate_on_submit():
        order = Order(user_id=current_user.id, total=total, status="pending",
                      reference=gen_ref("MN"), full_name=form.full_name.data,
                      phone=form.phone.data, address=form.address.data, notes=form.notes.data)
        db.session.add(order); db.session.flush()
        for it in items:
            db.session.add(OrderItem(order_id=order.id, product_id=it["product"].id,
                                     qty=it["qty"], unit_price=it["product"].price))
            it["product"].stock = max(0, it["product"].stock - it["qty"])
        db.session.commit()
        session["cart"] = {}; session.modified = True
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
        .order_by(Order.created_at.desc()).all()
    return render_template("shop/my_orders.html", orders=orders)


@shop_bp.route("/orders/<ref>")
@login_required
def order_detail(ref):
    o = Order.query.filter_by(reference=ref, user_id=current_user.id).first_or_404()
    return render_template("shop/order_detail.html", order=o)

from ...payments import is_configured as paystack_ready, initialize_transaction, verify_transaction
from flask import current_app


@shop_bp.route("/pay/<ref>")
@login_required
def pay(ref):
    """Start a Paystack payment for an order."""
    o = Order.query.filter_by(reference=ref, user_id=current_user.id).first_or_404()

    if o.payment_status == "paid":
        flash("This order is already paid.", "info")
        return redirect(url_for("shop.order_detail", ref=o.reference))

    if not paystack_ready():
        return render_template("shop/pay_manual.html", order=o)

    try:
        callback = url_for("shop.pay_callback", ref=o.reference, _external=True)
        amount_minor = int(float(o.total) * 100)

        data = initialize_transaction(
            email=current_user.email,
            amount_minor=amount_minor,
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
        current_app.logger.error(f"Paystack returned no auth URL: {data}")
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
    data = verify_transaction(ref)
    if data and data.get("status") == "success":
        o.payment_status = "paid"
        o.status = "paid"
        db.session.commit()
        flash(f"Payment received! Order {o.reference} confirmed.", "success")
    else:
        o.payment_status = "failed"
        db.session.commit()
        flash("Payment failed or was cancelled.", "warning")
    return redirect(url_for("shop.order_detail", ref=o.reference))