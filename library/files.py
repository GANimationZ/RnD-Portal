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

# At most this many files in ONE upload (one form submit). The total size of
# the whole request is capped separately by MAX_CONTENT_LENGTH (library/__init__.py).
MAX_FILES_PER_UPLOAD = 5


def get_extension(filename):
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def is_allowed(filename):
    return get_extension(filename) in ALLOWED_EXTENSIONS


def validate_uploads(files):
    """Check a list of uploaded files before saving anything.

    Returns an error message for the user, or None when everything is fine.
    Empty file fields (no filename) are ignored."""
    chosen = [f for f in files if f and f.filename]

    if len(chosen) > MAX_FILES_PER_UPLOAD:
        return (
            f"You can upload at most {MAX_FILES_PER_UPLOAD} files at once "
            f"(you selected {len(chosen)})."
        )

    for file in chosen:
        if not is_allowed(file.filename):
            return (
                f'File "{file.filename}" has an unsupported format. '
                "Use an image, PDF, Word, Excel, or PowerPoint file."
            )
    return None


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
