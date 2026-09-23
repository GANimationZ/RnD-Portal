"""Shared file upload helpers for issue_monitor and tv_design blueprints."""

import os
from datetime import datetime

from flask import current_app
from werkzeug.utils import secure_filename

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
DOCUMENT_EXTENSIONS = {
    "pdf": "pdf",
    "doc": "word", "docx": "word",
    "xls": "excel", "xlsx": "excel",
    "ppt": "ppt", "pptx": "ppt",
    "txt": "other",
}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | set(DOCUMENT_EXTENSIONS.keys())


def get_extension(filename):
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def is_allowed(filename):
    return get_extension(filename) in ALLOWED_EXTENSIONS


def get_file_type(filename):
    ext = get_extension(filename)
    if ext in IMAGE_EXTENSIONS:
        return "image"
    return DOCUMENT_EXTENSIONS.get(ext, "other")


def get_upload_dir(subdir):
    path = os.path.join(current_app.static_folder, "assets", "uploads", subdir)
    os.makedirs(path, exist_ok=True)
    return path


def save_upload(file, subdir, prefix):
    filename = f"{prefix}-{int(datetime.now().timestamp() * 1000)}-{secure_filename(file.filename)}"
    file.save(os.path.join(get_upload_dir(subdir), filename))
    return filename
