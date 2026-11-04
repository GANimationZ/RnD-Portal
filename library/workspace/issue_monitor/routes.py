from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, render_template, request, session

from library.auth import login_required, roles_required
from library.extensions import db
from library.files import is_allowed, get_file_type, save_upload
from library.models import CATEGORY_CHOICES, EVENT_CHOICES, Issue, IssueAttachment, User
from library.workspace.kpi_dashboard.recording import (
    record_assignment,
    record_completion,
    sync_overdue_flags,
)

issue_monitor_bp = Blueprint(
    "issue_monitor", __name__, url_prefix="/workspace/issue-monitor"
)

VALID_STATUS = {"Open", "Pending", "Closed", "On Hold"}

def _auto_mark_stale_as_pending():
    now = datetime.utcnow()
    open_issues = Issue.query.filter(Issue.status == "Open").all()
    for issue in open_issues:
        deadline_dt = datetime.combine(issue.deadline, datetime.min.time())
        midpoint = issue.created_at + (deadline_dt - issue.created_at) / 2
        if now >= midpoint:
            issue.status = "Pending"


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
    _auto_mark_stale_as_pending()
    db.session.commit()
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
    _auto_mark_stale_as_pending()
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
        return jsonify({"message": "All fields are required."}), 400

    if category not in CATEGORY_CHOICES or event not in EVENT_CHOICES:
        return jsonify({"message": "Invalid category or event."}), 400

    try:
        deadline = datetime.strptime(deadline_raw, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"message": "Invalid deadline format."}), 400
    
    MIN_DEADLINE_DAYS = 4
    if deadline < date.today() + timedelta(days=MIN_DEADLINE_DAYS):
        return jsonify({"message": f"Deadline must be at least {MIN_DEADLINE_DAYS} days from today."}), 400

    assignee_id = None
    if assignee_id_raw:
        candidate = User.query.get(assignee_id_raw)
        if not candidate or candidate.role != "Member" or not candidate.covers(category, event):
            return jsonify({"message": "Invalid assignee for this category/event."}), 400
        assignee_id = candidate.id

    for file in files:
        if file and file.filename and not is_allowed(file.filename):
            return jsonify({
                "message": f'File "{file.filename}" has an unsupported format. '
                           "Use an image, PDF, Word, Excel, or PowerPoint file."
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
    db.session.flush()

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
            issue.image_filename = filename

    if assignee_id:
        record_assignment(assignee_id)

    db.session.commit()

    return jsonify({"message": "Issue registered successfully.", "issue": issue.to_dict()}), 201


@issue_monitor_bp.route("/api/issues/<int:issue_id>/status", methods=["PATCH"])
@login_required
@roles_required("Super Admin", "Admin")
def api_update_status(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    assignee_id_raw = data.get("assignee_id")

    if status not in VALID_STATUS:
        return jsonify({"message": "Invalid status."}), 400

    if issue.status == "Closed":
        return jsonify({"message": "This issue is already closed and can no longer be changed."}), 400

    was_assigned_before = issue.assignee_id is not None

    if assignee_id_raw and not issue.assignee_id:
        candidate = User.query.get(assignee_id_raw)
        if not candidate or candidate.role != "Member" or not candidate.covers(issue.category, issue.event):
            return jsonify({"message": "Invalid assignee for this issue's category/event."}), 400
        issue.assignee_id = candidate.id

    issue.status = status

    if status == "Closed":
        issue.closed_at = datetime.utcnow()
        if issue.assignee_id:
            record_completion(issue.assignee_id, issue.created_at, already_assigned=was_assigned_before)

    db.session.commit()

    return jsonify({"message": "Status updated.", "issue": issue.to_dict()})