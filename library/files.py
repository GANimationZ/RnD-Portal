import os
from datetime import datetime

from flask import current_app
from werkzeug.utils import secure_filename

# Whole request (all files of one upload together) may not exceed this.
# Videos are the reason it is generous; the web server in front of the app
# (nginx: client_max_body_size) must allow at least the same size.
MAX_UPLOAD_SIZE_MB = 100

# At most this many files in ONE upload (one form submit).
MAX_FILES_PER_UPLOAD = 5

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "m4v", "ogv", "avi", "mkv"}
AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "ogg"}
ARCHIVE_EXTENSIONS = {"zip", "7z", "rar"}
DOCUMENT_EXTENSIONS = {
    "pdf": "pdf",
    "doc": "word", "docx": "word",
    "xls": "excel", "xlsx": "excel", "csv": "excel",
    "ppt": "ppt", "pptx": "ppt",
    "txt": "text",
}
# Only formats that are safe to serve back from /static (no html, svg, js, exe).
ALLOWED_EXTENSIONS = (
    IMAGE_EXTENSIONS
    | VIDEO_EXTENSIONS
    | AUDIO_EXTENSIONS
    | ARCHIVE_EXTENSIONS
    | set(DOCUMENT_EXTENSIONS)
)

# Size limit of a single file, in MB. Video and audio may use the whole
# request budget; everything else is capped lower.
DEFAULT_MAX_FILE_MB = 20
MAX_FILE_MB = {"video": MAX_UPLOAD_SIZE_MB, "audio": MAX_UPLOAD_SIZE_MB}

UPLOAD_HELP = "image, video, audio, PDF, Word, Excel, PowerPoint, text or ZIP"


def upload_accept():
    """Value for <input type="file" accept="..."> -- same list the server allows."""
    return ",".join(f".{ext}" for ext in sorted(ALLOWED_EXTENSIONS))


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
                f"Use an {UPLOAD_HELP} file."
            )
        limit_mb = MAX_FILE_MB.get(get_file_type(file.filename), DEFAULT_MAX_FILE_MB)
        if _file_size(file) > limit_mb * 1024 * 1024:
            return f'File "{file.filename}" is larger than {limit_mb} MB.'
    return None


def get_file_type(filename):
    ext = get_extension(filename)
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    if ext in ARCHIVE_EXTENSIONS:
        return "archive"
    return DOCUMENT_EXTENSIONS.get(ext, "other")


def _file_size(file):
    """Size in bytes of an uploaded file, without reading it into memory."""
    stream = file.stream
    position = stream.tell()
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(position)
    return size


def get_upload_dir(subdir):
    path = os.path.join(current_app.static_folder, "assets", "uploads", subdir)
    os.makedirs(path, exist_ok=True)
    return path


def save_upload(file, subdir, prefix):
    filename = f"{prefix}-{int(datetime.now().timestamp() * 1000)}-{secure_filename(file.filename)}"
    file.save(os.path.join(get_upload_dir(subdir), filename))
    return filename
