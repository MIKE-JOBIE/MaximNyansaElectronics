import os
import re
import secrets
import string
from werkzeug.utils import secure_filename
from flask import current_app


def slugify(text):
    text = re.sub(r"[^\w\s-]", "", str(text).lower()).strip()
    return re.sub(r"[-\s]+", "-", text)[:200]


def gen_ref(prefix="MN"):
    alphabet = string.ascii_uppercase + string.digits
    return prefix + "-" + "".join(secrets.choice(alphabet) for _ in range(8))


def _cloudinary_configured():
    return all([
        os.getenv("CLOUDINARY_CLOUD_NAME"),
        os.getenv("CLOUDINARY_API_KEY"),
        os.getenv("CLOUDINARY_API_SECRET"),
    ])


ALLOWED_DOC_EXT = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "csv"}


def external_url(endpoint, **values):
    """Absolute URL built from SITE_URL (not the request Host header) when configured."""
    from flask import url_for
    base = current_app.config.get("SITE_URL")
    if base:
        return base + url_for(endpoint, _external=False, **values)
    return url_for(endpoint, _external=True, **values)


def is_safe_next(target):
    """True only for same-site relative paths (blocks //evil.com and backslash tricks)."""
    from urllib.parse import urlparse
    if not target or "\\" in target or not target.startswith("/") or target.startswith("//"):
        return False
    p = urlparse(target)
    return not p.scheme and not p.netloc


def save_upload(file_storage, prefix="", preset=None, kind="image"):
    """
    Save an uploaded file safely. Returns a path/URL, or None if rejected.
    - kind="image": must be a real image; it is re-encoded as JPEG (strips payloads/EXIF).
    - kind="document": extension whitelist + basic signature check.
    Cloudinary is used if configured; otherwise local storage.
    """
    from flask import flash
    if not file_storage or not file_storage.filename:
        return None
    raw = file_storage.read()
    if not raw:
        return None
    filename = secure_filename(file_storage.filename) or "upload"
    resource_type = "image"

    if kind == "document":
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        ok = ext in ALLOWED_DOC_EXT
        if ext == "pdf":
            ok = ok and raw.startswith(b"%PDF")
        elif ext in ("docx", "pptx", "xlsx"):
            ok = ok and raw.startswith(b"PK")
        if not ok:
            flash("Unsupported or invalid file. Allowed: " + ", ".join(sorted(ALLOWED_DOC_EXT)), "danger")
            return None
        resource_type = "raw"
    else:
        try:
            from .images import resize_and_crop
            raw = resize_and_crop(raw, preset or "news")
            ext = "jpg"
        except Exception as e:
            current_app.logger.warning(f"Rejected image upload ({preset}): {e}")
            flash("That file is not a valid image (JPG, PNG, WEBP or GIF). Nothing was saved.", "danger")
            return None

    cloudinary_configured = _cloudinary_configured()
    if cloudinary_configured:
        try:
            import cloudinary
            import cloudinary.uploader
            cloudinary.config(
                cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
                api_key=os.getenv("CLOUDINARY_API_KEY"),
                api_secret=os.getenv("CLOUDINARY_API_SECRET"),
                secure=True,
            )
            public_id = f"{prefix}{secrets.token_hex(6)}" + (f".{ext}" if resource_type == "raw" else "")
            result = cloudinary.uploader.upload(raw, folder="maxim_nyansa",
                                                public_id=public_id, resource_type=resource_type)
            return result.get("secure_url")
        except Exception as e:
            current_app.logger.error(f"Cloudinary upload failed: {e}")
            flash("Media storage is temporarily unavailable. Nothing was saved.", "danger")
            return None

    unique = secrets.token_hex(6)
    base = filename.rsplit(".", 1)[0] if "." in filename else filename
    fname = f"{prefix}{unique}_{base}.{ext}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], fname)
    with open(path, "wb") as f:
        f.write(raw)
    return f"uploads/{fname}"


def is_external_url(path):
    """True if path is a full URL (Cloudinary etc.), False if it's a local static path."""
    return bool(path) and (path.startswith("http://") or path.startswith("https://"))

def audit_log(action, entity=None, entity_id=None, details=None):
    """Persist a security/accountability event without breaking the request if logging fails."""
    try:
        from flask_login import current_user
        from .extensions import db
        from .models import AuditLog
        from flask import request
        import json
        user_id = current_user.id if current_user.is_authenticated else None
        entry = AuditLog(
            user_id=user_id, action=str(action)[:120],
            entity=str(entity)[:80] if entity is not None else None,
            entity_id=str(entity_id)[:80] if entity_id is not None else None,
            details=json.dumps(details, default=str)[:4000] if details is not None else None,
            ip_address=(request.headers.get("X-Forwarded-For", request.remote_addr) or "")[:64],
            user_agent=(request.user_agent.string or "")[:500],
        )
        db.session.add(entry)
    except Exception:
        current_app.logger.exception("Audit logging failed")
