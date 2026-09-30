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


def save_upload(file_storage, prefix="", preset=None):
    """
    Save an uploaded file.
    - If preset is set, the image is center-cropped + resized before saving.
    - Cloudinary is used if configured; otherwise falls back to local storage.
    """
    if not file_storage or not file_storage.filename:
        return None

    raw = file_storage.read()

    # Resize if it's a preset image
    if preset:
        try:
            from .images import resize_and_crop
            raw = resize_and_crop(raw, preset)
            ext = "jpg"
        except Exception as e:
            current_app.logger.warning(f"Image resize failed ({preset}): {e}")
            ext = (file_storage.filename.rsplit(".", 1)[-1] or "jpg").lower()
    else:
        ext = (file_storage.filename.rsplit(".", 1)[-1] or "bin").lower()

    # Cloudinary path
    if _cloudinary_configured():
        try:
            import cloudinary
            import cloudinary.uploader
            cloudinary.config(
                cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
                api_key=os.getenv("CLOUDINARY_API_KEY"),
                api_secret=os.getenv("CLOUDINARY_API_SECRET"),
                secure=True,
            )
            result = cloudinary.uploader.upload(
                raw,
                folder="maxim_nyansa",
                public_id=f"{prefix}{secrets.token_hex(6)}",
                resource_type="image",
            )
            return result.get("secure_url")
        except Exception as e:
            current_app.logger.error(f"Cloudinary upload failed: {e}")

    # Local fallback
    unique = secrets.token_hex(6)
    safe_name = secure_filename(file_storage.filename or "upload") or "upload"
    base = safe_name.rsplit(".", 1)[0] if "." in safe_name else safe_name
    fname = f"{prefix}{unique}_{base}.{ext}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], fname)
    with open(path, "wb") as f:
        f.write(raw)
    return f"uploads/{fname}"


def is_external_url(path):
    """True if path is a full URL (Cloudinary etc.), False if it's a local static path."""
    return bool(path) and (path.startswith("http://") or path.startswith("https://"))