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


def save_upload(file_storage, prefix=""):
    """
    Save uploaded file.
    - If Cloudinary env vars are set → upload to Cloudinary, return the full URL.
    - Otherwise → save locally under static/uploads/, return 'uploads/filename'.
    """
    if not file_storage or not file_storage.filename:
        return None

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
                file_storage,
                folder="maxim_nyansa",
                public_id=f"{prefix}{secrets.token_hex(6)}_{secure_filename(file_storage.filename).rsplit('.',1)[0]}",
                resource_type="auto",
            )
            return result.get("secure_url")
        except Exception as e:
            current_app.logger.error(f"Cloudinary upload failed, falling back to local: {e}")
            # fall through to local save

    # Local fallback
    name = secure_filename(file_storage.filename)
    unique = secrets.token_hex(6)
    fname = f"{prefix}{unique}_{name}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], fname)
    file_storage.save(path)
    return f"uploads/{fname}"


def is_external_url(path):
    """True if path is a full URL (Cloudinary etc.), False if it's a local static path."""
    return bool(path) and (path.startswith("http://") or path.startswith("https://"))