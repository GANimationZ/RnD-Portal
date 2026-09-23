"""Issue Monitor blueprint: list/dashboard/register/priority-matrix pages
and their API endpoints."""

from datetime import datetime

from flask import Blueprint, jsonify, render_template, request, session

from library.auth import login_required, roles_required
from library.extensions import db
from library.files import is_allowed, get_file_type, save_upload
from library.models import Issue, IssueAttachment, User
from library.workspace.kpi_dashboard.recording import (
    record_assignment,
    record_completion,
    sync_overdue_flags,
)

issue_monitor_bp = Blueprint(
    "issue_monitor", __name__, url_prefix="/workspace/issue-monitor"
)

VALID_STATUS = {"Open", "Pending", "Closed", "On Hold"}


# ==================== Pages ====================

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

    # assignee_id is optional (open to anyone whose scope matches).
    # If given, must be a Member whose scope actually covers this
    # category/event -- never trust the client's value blindly.
    assignee_id = None
    if assignee_id_raw:
        candidate = User.query.get(assignee_id_raw)
        if not candidate or candidate.role != "Member" or not candidate.covers(category, event):
            return jsonify({"message": "Assignee tidak valid untuk category/event ini."}), 400
        assignee_id = candidate.id

    for file in files:
        if file and file.filename and not is_allowed(file.filename):
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
    db.session.flush()  # populate issue.id for attachments & KPI recording

    for file in files:
        if not (file and file.filename):
            continue
        filename = save_upload(file, "issues", "issue")
        db.session.add(IssueAttachment(
            issue_id=issue.id,
            filename=filename,
            original_name=file.filename,
            file_type=get_file_type(file.filename),
        ))
        if issue.image_filename is None and get_file_type(file.filename) == "image":
            issue.image_filename = filename  # backward compat for the old single-image view

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
    assignee_id_raw = data.get("assignee_id")  # optional: assign executor at close time

    if status not in VALID_STATUS:
        return jsonify({"message": "Status tidak valid."}), 400

    was_assigned_before = issue.assignee_id is not None

    # If this issue has no assignee yet and one is now provided (whether
    # closing or just updating status), validate and save it -- this is
    # the official path for "assign executor at close time".
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