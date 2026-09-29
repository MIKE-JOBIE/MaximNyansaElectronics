from flask import current_app, render_template_string
from flask_mail import Message
from .extensions import mail


def send_email(subject, recipients, html_body, text_body=None):
    """Send email via Flask-Mail. Falls back to console log if not configured."""
    if not current_app.config.get("MAIL_USERNAME"):
        # DEV MODE — print to console so you can copy reset links
        print("\n" + "=" * 70)
        print(f"📧 EMAIL (dev mode — not actually sent)")
        print(f"To:      {recipients}")
        print(f"Subject: {subject}")
        print("-" * 70)
        print(text_body or html_body)
        print("=" * 70 + "\n")
        return True

    try:
        msg = Message(subject=subject, recipients=recipients if isinstance(recipients, list) else [recipients])
        msg.html = html_body
        if text_body:
            msg.body = text_body
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Email send failed: {e}")
        return False


def send_password_reset_email(user, reset_url):
    subject = "Reset your Maxim Nyansa Electronics password"
    text = f"""
Hello {user.first_name or user.email},

You (or someone using your email) requested a password reset for your
Maxim Nyansa Electronics account.

Click this link to set a new password:

{reset_url}

This link expires in 1 hour. If you didn't request this, ignore this email.

— Maxim Nyansa Electronics
"""
    html = f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <h2 style="color:#8DC63F">Maxim Nyansa Electronics</h2>
  <p>Hello {user.first_name or user.email},</p>
  <p>You requested a password reset. Click the button below to set a new password:</p>
  <p style="text-align:center;margin:30px 0">
    <a href="{reset_url}" style="background:#8DC63F;color:#fff;padding:14px 28px;
       border-radius:999px;text-decoration:none;font-weight:bold">Reset Password</a>
  </p>
  <p style="font-size:13px;color:#666">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
  <p style="font-size:13px;color:#666">— Maxim Nyansa Electronics, Freetown</p>
</div>
"""
    return send_email(subject, [user.email], html, text)