import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from ...models import User, PasswordResetToken
from ...forms import RegisterForm, LoginForm, ForgotPasswordForm, ResetPasswordForm, ProfileForm, ChangePasswordForm
from ...extensions import db
from ...email_utils import send_password_reset_email

auth_bp = Blueprint("auth", __name__, template_folder="../../templates/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("Email already registered.", "danger")
        else:
            u = User(email=form.email.data.lower(), first_name=form.first_name.data,
                     last_name=form.last_name.data, phone=form.phone.data, role="trainee")
            u.set_password(form.password.data)
            db.session.add(u)
            db.session.commit()
            login_user(u)
            flash("Welcome to Maxim Nyansa!", "success")
            return redirect(url_for("main.index"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        u = User.query.filter_by(email=form.email.data.lower()).first()
        if u and u.check_password(form.password.data) and u.is_active:
            login_user(u, remember=(form.remember.data == "yes"))
            flash(f"Welcome back, {u.first_name or 'friend'}!", "success")
            nxt = request.args.get("next")
            if nxt and nxt.startswith("/"):
                return redirect(nxt)
            return redirect(url_for("admin.dashboard") if u.is_admin else url_for("main.index"))
        flash("Invalid credentials.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/profile")
@login_required
def profile():
    return render_template("auth/profile.html")


@auth_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def profile_edit():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name  = form.last_name.data
        current_user.phone      = form.phone.data
        current_user.address    = form.address.data
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/profile_edit.html", form=form)


@auth_bp.route("/profile/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(form.password.data)
            db.session.commit()
            flash("Password updated.", "success")
            return redirect(url_for("auth.profile"))
    return render_template("auth/change_password.html", form=form)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        u = User.query.filter_by(email=form.email.data.lower()).first()
        # Always show success message — never reveal if email exists
        if u:
            token = secrets.token_urlsafe(48)
            prt = PasswordResetToken(user_id=u.id, token=token,
                                     expires_at=datetime.utcnow() + timedelta(hours=1))
            db.session.add(prt)
            db.session.commit()
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            send_password_reset_email(u, reset_url)
        flash("If that email exists, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    prt = PasswordResetToken.query.filter_by(token=token).first()
    if not prt or not prt.is_valid:
        flash("Invalid or expired reset link.", "danger")
        return redirect(url_for("auth.forgot_password"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        prt.user.set_password(form.password.data)
        prt.used = True
        db.session.commit()
        flash("Password reset. You can now log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form, token=token)