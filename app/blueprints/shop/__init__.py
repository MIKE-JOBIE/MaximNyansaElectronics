from flask import Blueprint, render_template, redirect, url_for, flash, session, request, abort
from flask_login import login_required, current_user
from ...models import Product, Category, Order, OrderItem
from ...forms import CheckoutForm
from ...extensions import db
from ...utils import gen_ref

shop_bp = Blueprint("shop", __name__, template_folder="../../templates/shop")

def _cart(): return session.setdefault("cart", {})

@shop_bp.route("/")
def index():
    cat_slug = request.args.get("cat")
    q = request.args.get("q","").strip()
    query = Product.query.filter_by(is_active=True)
    if cat_slug:
        c = Category.query.filter_by(slug=cat_slug).first()
        if c: query = query.filter_by(category_id=c.id)
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    products = query.order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
    return render_template("shop/index.html", products=products, categories=categories, current_cat=cat_slug, q=q)

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
    flash(f"Added {p.name} to cart.", "success")
    return redirect(request.referrer or url_for("shop.index"))

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