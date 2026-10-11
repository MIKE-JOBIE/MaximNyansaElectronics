import json
from datetime import datetime, timedelta

from flask import current_app
from flask_mail import Message
from markupsafe import escape

from .extensions import db, mail


def _build(subject, recipients, html_body, text_body):
    normalized = recipients if isinstance(recipients, list) else [recipients]
    msg = Message(subject=subject, recipients=normalized)
    msg.html = html_body
    if text_body:
        msg.body = text_body
    return msg


def send_email(subject, recipients, html_body, text_body=None):
    """Send one email synchronously. Development without SMTP prints a preview only."""
    if not current_app.config.get("MAIL_USERNAME"):
        if current_app.debug or current_app.testing:
            print("\n" + "=" * 70)
            print("EMAIL (dev mode - not actually sent)")
            print(f"To:      {recipients}")
            print(f"Subject: {subject}")
            print("-" * 70)
            print(text_body or html_body)
            print("=" * 70 + "\n")
            return True
        current_app.logger.warning("Email not sent: MAIL_USERNAME is not configured (subject=%r)", subject)
        return False
    try:
        mail.send(_build(subject, recipients, html_body, text_body))
        return True
    except Exception:
        # Do not log message bodies or reset links.
        current_app.logger.exception("Email send failed (subject=%r)", subject)
        return False


def send_many_async(messages):
    """
    Persist outbound mail to PostgreSQL instead of relying on a disposable worker thread.
    Delivery is at-least-once: a process crash after SMTP acceptance but before commit
    can cause a retry. Keep the batch small and use provider-side deduplication where possible.
    """
    if current_app.testing or current_app.debug:
        for subject, recipients, html_body, text_body in messages:
            send_email(subject, recipients, html_body, text_body)
        return True

    from .models import EmailJob
    try:
        for subject, recipients, html_body, text_body in messages:
            normalized = recipients if isinstance(recipients, list) else [recipients]
            db.session.add(EmailJob(
                subject=str(subject)[:255],
                recipients=json.dumps([str(item) for item in normalized]),
                html_body=html_body or "",
                text_body=text_body,
                status="queued",
                attempts=0,
                available_at=datetime.utcnow(),
            ))
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Could not queue outbound email")
        return False


def process_email_queue(limit=10):
    """Send a bounded batch of due email jobs; caller must authenticate maintenance access."""
    from .models import EmailJob

    if not current_app.config.get("MAIL_USERNAME"):
        current_app.logger.warning("Email queue paused: MAIL_USERNAME is not configured")
        return {"sent": 0, "failed": 0, "paused": True}

    now = datetime.utcnow()
    safe_limit = max(1, min(int(limit), 25))
    jobs = (EmailJob.query
            .filter(EmailJob.status == "queued", EmailJob.available_at <= now,
                    EmailJob.attempts < 5)
            .order_by(EmailJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(safe_limit).all())
    sent = failed = 0

    # Keep the row locks until the whole small batch commits, so two maintenance
    # workers cannot claim the same queued rows simultaneously.
    for job in jobs:
        try:
            recipients = json.loads(job.recipients)
            if not isinstance(recipients, list) or not recipients:
                raise ValueError("Email job has no valid recipients")
            mail.send(_build(job.subject, recipients, job.html_body, job.text_body))
            job.status = "sent"
            job.sent_at = datetime.utcnow()
            job.last_error = None
            sent += 1
        except Exception as exc:
            job.attempts = (job.attempts or 0) + 1
            job.last_error = type(exc).__name__[:1000]
            if job.attempts >= 5:
                job.status = "failed"
            else:
                job.status = "queued"
                job.available_at = datetime.utcnow() + timedelta(seconds=min(3600, 60 * (2 ** (job.attempts - 1))))
            failed += 1
            current_app.logger.warning("Email job %s failed (attempt %s): %s",
                                       job.id, job.attempts, type(exc).__name__)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Email queue batch commit failed")
        return {"sent": 0, "failed": len(jobs), "paused": False, "error": "commit_failed"}
    return {"sent": sent, "failed": failed, "paused": False}


def send_password_reset_email(user, reset_url):
    subject = "Reset your Maxim Nyansa Electronics password"
    name = user.first_name or user.email
    text = f"""
Hello {name},

You (or someone using your email) requested a password reset for your
Maxim Nyansa Electronics account.

Click this link to set a new password:

{reset_url}

This link expires in 1 hour. If you didn't request this, ignore this email.

- Maxim Nyansa Electronics
"""
    html = f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <h2 style="color:#8DC63F">Maxim Nyansa Electronics</h2>
  <p>Hello {escape(name)},</p>
  <p>You requested a password reset. Click the button below to set a new password:</p>
  <p style="text-align:center;margin:30px 0">
    <a href="{escape(reset_url)}" style="background:#8DC63F;color:#fff;padding:14px 28px;
       border-radius:999px;text-decoration:none;font-weight:bold">Reset Password</a>
  </p>
  <p style="font-size:13px;color:#666">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
  <p style="font-size:13px;color:#666">- Maxim Nyansa Electronics, Freetown</p>
</div>
"""
    return send_many_async([(subject, [user.email], html, text)])
