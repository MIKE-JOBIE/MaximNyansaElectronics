from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ...models import User
from ...forms import RegisterForm, LoginForm
from ...extensions import db

auth_bp = Blueprint("auth", __name__, template_folder="../../templates/auth")

@auth_bp.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated: return redirect(url_for("main.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("Email already registered.", "danger")
        else:
            u = User(email=form.email.data.lower(), first_name=form.first_name.data,
                     last_name=form.last_name.data, phone=form.phone.data, role="trainee")
            u.set_password(form.password.data)
            db.session.add(u); db.session.commit()
            login_user(u)
            flash("Welcome to Maxim Nyansa!", "success")
            return redirect(url_for("main.index"))
    return render_template("auth/register.html", form=form)

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated: return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        u = User.query.filter_by(email=form.email.data.lower()).first()
        if u and u.check_password(form.password.data) and u.is_active:
            login_user(u, remember=(form.remember.data=="yes"))
            flash(f"Welcome back, {u.first_name or 'friend'}!", "success")
            nxt = request.args.get("next")
            if nxt and nxt.startswith("/"): return redirect(nxt)
            return redirect(url_for("admin.dashboard") if u.is_admin else url_for("main.index"))
        flash("Invalid credentials.", "danger")
    return render_template("auth/login.html", form=form)

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user(); flash("Logged out.", "info"); return redirect(url_for("main.index"))

@auth_bp.route("/profile")
@login_required
def profile():
    return render_template("auth/profile.html")