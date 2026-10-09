from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from functools import wraps
from markupsafe import escape
from ...extensions import db
from ...models import Application, Program
from ...forms import BulkEmailForm
from ...email_utils import send_many_async


def admin_required(f):
    @wraps(f)
    def w(*a, **kw):
        if not current_user.is_authenticated or not current_user.is_admin:
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

            seen, recipients = set(), []
            for a in apps:
                if a.applicant and a.applicant.email and a.applicant.id not in seen:
                    recipients.append(a.applicant)
                    seen.add(a.applicant.id)

            subject = form.subject.data
            safe_subject = escape(subject)
            safe_body = str(escape(form.body.data))   # admin text is shown as text, never as HTML
            messages = []
            for u in recipients:
                text = form.body.data.replace("{{name}}", u.first_name or "friend").replace("{{email}}", u.email)
                html_body = safe_body.replace("{{name}}", str(escape(u.first_name or "friend"))) \
                                     .replace("{{email}}", str(escape(u.email)))
                html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;padding:20px">
<h3 style="color:#8DC63F">{safe_subject}</h3>
<div style="white-space:pre-wrap;line-height:1.6">{html_body}</div>
<hr style="margin:24px 0;border:none;border-top:1px solid #eee">
<p style="font-size:12px;color:#888">— Maxim Nyansa Electronics, Freetown</p>
</div>"""
                messages.append((subject, [u.email], html, text))

            send_many_async(messages)      # sent in the background; the page returns at once
            flash(f"Queued {len(messages)} email(s) for sending.", "success")
            return redirect(url_for("admin.bulk_email"))

        return render_template("admin/bulk_email.html", form=form)
