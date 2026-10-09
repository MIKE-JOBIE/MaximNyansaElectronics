from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from ...extensions import db
from ...models import SiteSetting
from ...settings_utils import DEFAULTS, invalidate_cache

def admin_required(f):
    @wraps(f)
    def w(*a, **kw):
        if not current_user.is_authenticated or not current_user.is_admin:
            from flask import abort
            abort(403)
        return f(*a, **kw)
    return w


def register_settings_routes(bp):
    @bp.route("/settings", methods=["GET", "POST"])
    @login_required
    @admin_required
    def settings():
        if request.method == "POST":
            for key in request.form:
                if key.startswith("field_") and key[6:] in DEFAULTS:   # only known settings
                    SiteSetting.set(key[6:], request.form[key])
            # Handle checkboxes (they don't appear if unchecked)
            SiteSetting.set("announcement_active",
                            "true" if request.form.get("announcement_active") == "on" else "false")
            invalidate_cache()
            flash("Settings saved.", "success")
            return redirect(url_for("admin.settings"))

        current = {}
        for key in DEFAULTS:
            current[key] = SiteSetting.get(key, DEFAULTS[key])
        return render_template("admin/settings.html", settings=current)