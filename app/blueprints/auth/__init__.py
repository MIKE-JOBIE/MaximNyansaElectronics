import hashlib
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from ...models import User, PasswordResetToken
from ...forms import (RegisterForm, LoginForm, ForgotPasswordForm,
                      ResetPasswordForm, ProfileForm, ChangePasswordForm)
from ...extensions import db, rate_limit
from ...email_utils import send_password_reset_email
from ...utils import external_url, is_safe_next


auth_bp = Blueprint("auth", __name__, template_folder="../../templates/auth")

# Used to keep login timing the same whether or not the email exists
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def _hash_token(raw):
    """Reset tokens are stored hashed, so a database leak cannot be used to reset accounts."""
    return hashlib.sha256(raw.encode()).hexdigest()


def _login_key():
    """Rate-limit per target account as well as per IP, to slow password guessing."""
    return "login:" + (request.form.get("email", "").strip().lower() or (request.remote_addr or "?"))


# --- REGISTER ----------------------------------------------------------------
@auth_bp.route("/register", methods=["GET", "POST"])
@rate_limit("5 per minute", methods=["POST"])
@rate_limit("20 per hour", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.strip().lower()).first():
            flash("Email already registered.", "danger")
        else:
            u = User(email=form.email.data.strip().lower(),
                     first_name=form.first_name.data,
                     last_name=form.last_name.data,
                     phone=form.phone.data,
                     role="trainee")
            u.set_password(form.password.data)
            db.session.add(u)
            db.session.commit()
            login_user(u)
            flash("Welcome to Maxim Nyansa!", "success")
            return redirect(url_for("main.index"))
    return render_template("auth/register.html", form=form)


# --- LOGIN -------------------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
@rate_limit("10 per minute", methods=["POST"])
@rate_limit("10 per hour", key_func=_login_key, methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        u = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if u is None:
            check_password_hash(_DUMMY_HASH, form.password.data)  # equalise timing
        if u and u.check_password(form.password.data) and u.is_active:
            login_user(u, remember=(form.remember.data == "yes"))
            flash(f"Welcome back, {u.first_name or 'friend'}!", "success")
            nxt = request.args.get("next")
            if is_safe_next(nxt):
                return redirect(nxt)
            return redirect(url_for("admin.dashboard") if u.is_admin else url_for("main.index"))
        flash("Invalid credentials.", "danger")
    return render_template("auth/login.html", form=form)


# --- LOGOUT ------------------------------------------------------------------
@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("main.index"))


# --- PROFILE -----------------------------------------------------------------
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
        current_user.last_name = form.last_name.data
        current_user.phone = form.phone.data
        current_user.address = form.address.data
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/profile_edit.html", form=form)


@auth_bp.route("/profile/change-password", methods=["GET", "POST"])
@login_required
@rate_limit("10 per hour", methods=["POST"])
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current.data):
            flash("Current password is incorrect.", "danger")
        else:
            user = current_user._get_current_object()
            user.set_password(form.password.data)
            db.session.commit()
            # All other sessions are now invalid; keep this one signed in
            login_user(user)
            flash("Password updated. Other devices have been signed out.", "success")
            return redirect(url_for("auth.profile"))
    return render_template("auth/change_password.html", form=form)


# --- PASSWORD RESET ----------------------------------------------------------
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@rate_limit("3 per minute", methods=["POST"])
@rate_limit("10 per hour", methods=["POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        u = User.query.filter_by(email=form.email.data.strip().lower()).first()
        # Always show the same message - never reveal whether the email exists
        if u:
            raw = secrets.token_urlsafe(48)
            PasswordResetToken.query.filter_by(user_id=u.id, used=False).update({"used": True})
            db.session.add(PasswordResetToken(
                user_id=u.id,
                token=_hash_token(raw),
                expires_at=datetime.utcnow() + timedelta(hours=1),
            ))
            db.session.commit()
            send_password_reset_email(u, external_url("auth.reset_password", token=raw))
        flash("If that email exists, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@rate_limit("20 per hour", methods=["POST"])
def reset_password(token):
    prt = PasswordResetToken.query.filter_by(token=_hash_token(token)).first()
    if not prt or not prt.is_valid:
        flash("Invalid or expired reset link.", "danger")
        return redirect(url_for("auth.forgot_password"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        prt.user.set_password(form.password.data)   # also signs out every existing session
        PasswordResetToken.query.filter_by(user_id=prt.user_id, used=False).update({"used": True})
        db.session.commit()
        flash("Password reset. You can now log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form, token=token)
