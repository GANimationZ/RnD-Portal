"""
Flask blueprint Issue Monitor.

- Halaman `/workspace/issue-monitor` (list/dashboard/register/priority
  matrix, semuanya di satu template lewat tab JS) dan halaman detail
  `/workspace/issue-monitor/<id>` ("lihat issue kayak id=1").
- Data issue disimpan di tabel `issues` (lihat library/models.py), BUKAN
  dummy array di JS lagi.
- Lampiran (gambar, Word, Excel, PowerPoint -- boleh lebih dari satu file
  sekaligus) disimpan sebagai file asli di static/assets/upload/, DB cuma
  nyimpen nama file lewat tabel `issue_attachments`.
- Assignee (Pelaksana) OPSIONAL saat issue dibuat -- boleh dibiarkan
  kosong ("siapa saja di tim yang cocok category+event boleh ambil").
  Kalau assignee memang belum ditentukan saat issue dibuat, QA tetap bisa
  menentukan siapa yang mengerjakan PAS MENUTUP issue-nya (poin 4), lewat
  field `assignee_id` opsional di body PATCH /status -- supaya tetap
  tercatat di KPI Dashboard orang yang bersangkutan (lihat recording.py).
"""

import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request, session
from werkzeug.utils import secure_filename

from library.auth import login_required, roles_required
from library.extensions import db
from library.models import Issue, IssueAttachment, User
from library.workspace.kpi_dashboard.recording import (
    record_assignment,
    record_completion,
    sync_overdue_flags,
)

issue_monitor_bp = Blueprint(
    "issue_monitor", __name__, url_prefix="/workspace/issue-monitor"
)

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
DOCUMENT_EXTENSIONS = {
    "pdf": "pdf",
    "doc": "word", "docx": "word",
    "xls": "excel", "xlsx": "excel",
    "ppt": "ppt", "pptx": "ppt",
    "txt": "other",
}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | set(DOCUMENT_EXTENSIONS.keys())
VALID_STATUS = {"Open", "Pending", "Closed", "On Hold"}
UPLOAD_SUBDIR = os.path.join("assets", "upload")


def _extension(filename):
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def _allowed_file(filename):
    return _extension(filename) in ALLOWED_EXTENSIONS


def _file_type(filename):
    ext = _extension(filename)
    if ext in IMAGE_EXTENSIONS:
        return "image"
    return DOCUMENT_EXTENSIONS.get(ext, "other")


def _upload_dir():
    path = os.path.join(current_app.static_folder, UPLOAD_SUBDIR)
    os.makedirs(path, exist_ok=True)
    return path


def _save_upload(file):
    ext = _extension(file.filename)
    filename = f"issue-{int(datetime.now().timestamp() * 1000)}-{secure_filename(file.filename)}"
    file.save(os.path.join(_upload_dir(), filename))
    return filename


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
    sync_overdue_flags()
    db.session.commit()
    issues = Issue.query.order_by(Issue.id.desc()).all()
    return jsonify({"issues": [i.to_dict() for i in issues]})


@issue_monitor_bp.route("/api/issues", methods=["POST"])
@login_required
@roles_required("Super Admin", "Admin")
def api_create_issue():
    title = (request.form.get("title") or "").strip()
    category = (request.form.get("category") or "").strip()
    event = (request.form.get("event") or "").strip()
    description = (request.form.get("description") or "").strip()
    deadline_raw = (request.form.get("deadline") or "").strip()  # format Y-m-d
    assignee_id_raw = (request.form.get("assignee_id") or "").strip()
    files = request.files.getlist("attachments") or ([request.files["image"]] if request.files.get("image") else [])

    if not all([title, category, event, description, deadline_raw]):
        return jsonify({"message": "Semua field wajib diisi."}), 400

    try:
        deadline = datetime.strptime(deadline_raw, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"message": "Format deadline tidak valid."}), 400

    # assignee_id BENAR-BENAR opsional -- boleh dikosongi kalau issue-nya
    # terbuka untuk siapa saja di tim yang cocok category+event (poin 4).
    # Kalau diisi, harus Member yang scope-nya memang mencakup category &
    # event ini (tidak percaya begitu saja ke value dari client).
    assignee_id = None
    if assignee_id_raw:
        candidate = User.query.get(assignee_id_raw)
        if not candidate or candidate.role != "Member" or not candidate.covers(category, event):
            return jsonify({"message": "Assignee tidak valid untuk category/event ini."}), 400
        assignee_id = candidate.id

    for file in files:
        if file and file.filename and not _allowed_file(file.filename):
            return jsonify({
                "message": f'Format file "{file.filename}" tidak didukung. '
                           "Gunakan gambar, PDF, Word, Excel, atau PowerPoint."
            }), 400

    issue = Issue(
        title=title,
        description=description,
        category=category,
        event=event,
        deadline=deadline,
        owner_name=session.get("username", "Admin"),
        assignee_id=assignee_id,
        priority="Medium",
        status="Open",
    )
    db.session.add(issue)
    db.session.flush()  # supaya issue.id kebentuk buat attachment & id kembalian ke KPI

    for file in files:
        if not (file and file.filename):
            continue
        filename = _save_upload(file)
        db.session.add(IssueAttachment(
            issue_id=issue.id,
            filename=filename,
            original_name=file.filename,
            file_type=_file_type(file.filename),
        ))
        if issue.image_filename is None and _file_type(file.filename) == "image":
            issue.image_filename = filename  # kompatibilitas tampilan gambar lama

    if assignee_id:
        record_assignment(assignee_id)

    db.session.commit()

    return jsonify({"message": "Issue berhasil didaftarkan.", "issue": issue.to_dict()}), 201


@issue_monitor_bp.route("/api/issues/<int:issue_id>/status", methods=["PATCH"])
@login_required
@roles_required("Super Admin", "Admin")
def api_update_status(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    assignee_id_raw = data.get("assignee_id")  # opsional: "assign pelaksana di akhir"

    if status not in VALID_STATUS:
        return jsonify({"message": "Status tidak valid."}), 400

    was_assigned_before = issue.assignee_id is not None

    # Kalau issue ini belum ada assignee-nya dan sekarang dikasih satu
    # (baik saat ditutup maupun sekadar update status lain), validasi &
    # simpan -- ini jalan resmi buat "assign pelaksana di akhir" (poin 4).
    if assignee_id_raw and not issue.assignee_id:
        candidate = User.query.get(assignee_id_raw)
        if not candidate or candidate.role != "Member" or not candidate.covers(issue.category, issue.event):
            return jsonify({"message": "Assignee tidak valid untuk category/event issue ini."}), 400
        issue.assignee_id = candidate.id

    issue.status = status

    if status == "Closed":
        issue.closed_at = datetime.utcnow()
        if issue.assignee_id:
            record_completion(issue.assignee_id, issue.created_at, already_assigned=was_assigned_before)

    db.session.commit()

    return jsonify({"message": "Status diperbarui.", "issue": issue.to_dict()})