"""
Flask blueprint Issue Monitor.

- Halaman `/workspace/issue-monitor` (list/dashboard/register/priority
  matrix, semuanya di satu template lewat tab JS) dan halaman detail
  `/workspace/issue-monitor/<id>` ("lihat issue kayak id=1").
- Data issue disimpan di tabel `issues` (lihat library/models.py), BUKAN
  dummy array di JS lagi.
- Gambar yang di-upload lewat form Register disimpan sebagai file asli di
  static/assets/upload/ (nama folder sengaja "upload", ikut yang sudah ada
  di project), DB cuma nyimpen nama filenya.
"""

import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request, session
from werkzeug.utils import secure_filename

from library.auth import login_required
from library.extensions import db
from library.models import Issue, User

issue_monitor_bp = Blueprint(
    "issue_monitor", __name__, url_prefix="/workspace/issue-monitor"
)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
VALID_STATUS = {"Open", "Pending", "Closed", "On Hold"}
UPLOAD_SUBDIR = os.path.join("assets", "upload")


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _upload_dir():
    path = os.path.join(current_app.static_folder, UPLOAD_SUBDIR)
    os.makedirs(path, exist_ok=True)
    return path


# ==================== Halaman ====================

@issue_monitor_bp.route("", methods=["GET"])
@login_required
def index():
    all_users = User.query.order_by(User.username).all()
    return render_template(
        "workspace/issue_monitor.html",
        active_nav="issue-monitor",
        username=session.get("username"),
        users=all_users,
    )


@issue_monitor_bp.route("/<int:issue_id>", methods=["GET"])
@login_required
def detail(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    return render_template(
        "workspace/issue_detail.html",
        active_nav="issue-monitor",
        username=session.get("username"),
        issue=issue,
    )


# ==================== API ====================

@issue_monitor_bp.route("/api/issues", methods=["GET"])
@login_required
def api_list_issues():
    issues = Issue.query.order_by(Issue.id.desc()).all()
    return jsonify({"issues": [i.to_dict() for i in issues]})


@issue_monitor_bp.route("/api/issues", methods=["POST"])
@login_required
def api_create_issue():
    title = (request.form.get("title") or "").strip()
    category = (request.form.get("category") or "").strip()
    event = (request.form.get("event") or "").strip()
    description = (request.form.get("description") or "").strip()
    deadline_raw = (request.form.get("deadline") or "").strip()  # format Y-m-d
    file = request.files.get("image")

    if not all([title, category, event, description, deadline_raw]):
        return jsonify({"message": "Semua field wajib diisi."}), 400

    try:
        deadline = datetime.strptime(deadline_raw, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"message": "Format deadline tidak valid."}), 400

    image_filename = None
    if file and file.filename:
        if not _allowed_file(file.filename):
            return jsonify({"message": "Format gambar tidak didukung. Gunakan PNG/JPG/JPEG/GIF/WEBP."}), 400
        ext = file.filename.rsplit(".", 1)[1].lower()
        image_filename = f"issue-{int(datetime.now().timestamp())}-{secure_filename(file.filename)}"
        file.save(os.path.join(_upload_dir(), image_filename))

    issue = Issue(
        title=title,
        description=description,
        category=category,
        event=event,
        deadline=deadline,
        image_filename=image_filename,
        owner_name=session.get("username", "Admin"),
        priority="Medium",
        status="Open",
    )
    db.session.add(issue)
    db.session.commit()

    return jsonify({"message": "Issue berhasil didaftarkan.", "issue": issue.to_dict()}), 201


@issue_monitor_bp.route("/api/issues/<int:issue_id>/status", methods=["PATCH"])
@login_required
def api_update_status(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json(silent=True) or {}
    status = data.get("status")

    if status not in VALID_STATUS:
        return jsonify({"message": "Status tidak valid."}), 400

    issue.status = status
    db.session.commit()

    return jsonify({"message": "Status diperbarui.", "issue": issue.to_dict()})