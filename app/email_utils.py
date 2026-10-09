import threading

from flask import current_app
from flask_mail import Message
from markupsafe import escape

from .extensions import mail


def _build(subject, recipients, html_body, text_body):
    msg = Message(subject=subject, recipients=recipients if isinstance(recipients, list) else [recipients])
    msg.html = html_body
    if text_body:
        msg.body = text_body
    return msg


def send_email(subject, recipients, html_body, text_body=None):
    """Send one email. In dev (debug/testing, no SMTP) print it; in production just log."""
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
        # Never write message bodies (they can contain reset links) to production logs
        current_app.logger.warning("Email not sent: MAIL_USERNAME is not configured (subject=%r)", subject)
        return False
    try:
        mail.send(_build(subject, recipients, html_body, text_body))
        return True
    except Exception as e:
        current_app.logger.error(f"Email send failed: {e}")
        return False


def send_many_async(messages):
    """
    Send a batch in a background thread so the web request returns immediately.
    messages: list of (subject, recipients, html_body, text_body).
    NOTE: stop-gap. For heavy volume use a real queue (RQ/Celery) so nothing is lost on restart.
    """
    app = current_app._get_current_object()

    def worker():
        with app.app_context():
            sent = failed = 0
            try:
                with mail.connect() as conn:
                    for subject, recipients, html, text in messages:
                        try:
                            conn.send(_build(subject, recipients, html, text))
                            sent += 1
                        except Exception as e:
                            failed += 1
                            app.logger.error(f"Email send failed: {e}")
            except Exception as e:
                app.logger.error(f"Email batch failed: {e}")
            app.logger.info("Email batch finished: %s sent, %s failed", sent, failed)

    if not app.config.get("MAIL_USERNAME"):
        for subject, recipients, html, text in messages:
            send_email(subject, recipients, html, text)
        return
    threading.Thread(target=worker, daemon=True).start()


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
    # Sent in the background so response time does not reveal whether the email exists
    send_many_async([(subject, [user.email], html, text)])
    return True
