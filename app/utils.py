import os, re, secrets, string
from werkzeug.utils import secure_filename
from flask import current_app

def slugify(text):
    text = re.sub(r"[^\w\s-]", "", str(text).lower()).strip()
    return re.sub(r"[-\s]+", "-", text)[:200]

def save_upload(file_storage, prefix=""):
    if not file_storage or not file_storage.filename:
        return None
    name = secure_filename(file_storage.filename)
    unique = secrets.token_hex(6)
    fname = f"{prefix}{unique}_{name}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], fname)
    file_storage.save(path)
    return f"uploads/{fname}"

def gen_ref(prefix="MN"):
    alphabet = string.ascii_uppercase + string.digits
    return prefix + "-" + "".join(secrets.choice(alphabet) for _ in range(8))