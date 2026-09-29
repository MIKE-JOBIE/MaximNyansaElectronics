from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from ...extensions import db
from ...models import Application, Program
from ...forms import BulkEmailForm
from ...email_utils import send_email


def admin_required(f):
    @wraps(f)
    def w(*a, **kw):
        if not current_user.is_authenticated or not current_user.is_admin:
            from flask import abort
            abort(403)
        return f(*a, **kw)
    return w


def register_bulk_routes(bp):
    @bp.route("/bulk-email", methods=["GET", "POST"])
    @login_required
    @admin_required
    def bulk_email():
        form = BulkEmailForm()
        programs = Program.query.order_by(Program.title).all()
        form.program_id.choices = [(0, "— All programs —")] + [(p.id, p.title) for p in programs]

        if form.validate_on_submit():
            q = Application.query
            if form.program_id.data:
                q = q.filter_by(program_id=form.program_id.data)
            if form.status.data != "all":
                q = q.filter_by(status=form.status.data)

            apps = q.all()
            if not apps:
                flash("No recipients match those filters.", "warning")
                return redirect(url_for("admin.bulk_email"))

            # unique users
            seen = set()
            recipients = []
            for a in apps:
                if a.applicant and a.applicant.email and a.applicant.id not in seen:
                    recipients.append(a.applicant)
                    seen.add(a.applicant.id)

            sent, failed = 0, 0
            for u in recipients:
                personalized = form.body.data.replace("{{name}}", u.first_name or "friend") \
                                             .replace("{{email}}", u.email)
                html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;padding:20px">
<h3 style="color:#8DC63F">{form.subject.data}</h3>
<div style="white-space:pre-wrap;line-height:1.6">{personalized}</div>
<hr style="margin:24px 0;border:none;border-top:1px solid #eee">
<p style="font-size:12px;color:#888">— Maxim Nyansa Electronics, Freetown</p>
</div>"""
                if send_email(form.subject.data, [u.email], html, personalized):
                    sent += 1
                else:
                    failed += 1

            flash(f"Sent {sent} email(s). {failed} failed.", "success" if failed == 0 else "warning")
            return redirect(url_for("admin.bulk_email"))

        return render_template("admin/bulk_email.html", form=form)