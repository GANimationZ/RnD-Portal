"""KPI Dashboard blueprint.

- User (role="Member") + KPIRecord + BestPractice are the data source,
  portable across SQLite/PostgreSQL.
- All calculations (workload bar, completion rate, leaderboard, range
  aggregation) live in metrics.py -- these routes just query the DB and
  call metrics.py, returning ready-to-render JSON.
- /api/* is shared by the Individual/Team panels (live) and the History
  sub-panels, so Recent/Last Week/Last Month/Last Year stay consistent
  everywhere. Export (per selected month) and the .xlsx snapshot history
  are a separate, archival-only feature.
"""

import os
import re
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, send_file

from library.auth import login_required
from library.extensions import db
from library.models import BestPractice, User

from .kpi_excel import (
    build_individual_workbook,
    build_team_workbook,
    period_label_from_key,
    workbook_to_bytes,
    parse_employee_workbook,
)
from .metrics import (
    DEFAULT_RANGE,
    RANGE_LABELS,
    employee_insights,
    employee_list_summary,
    employee_summary,
    team_summary,
)

kpi_dashboard_bp = Blueprint("kpi_dashboard", __name__, url_prefix="/workspace/kpi-dashboard")


@kpi_dashboard_bp.before_request
@login_required
def _restrict_kpi_dashboard():
    """QA (role "Admin") has no access to KPI Dashboard at all -- page or
    API. Enforced as before_request (not a per-route decorator) so no
    endpoint can be added later without this protection.

    Uses abort(403) so the shared error handler (library/errors.py) picks
    the format: JSON for API/fetch calls, the 403 page for plain browser
    navigation (e.g. export/history downloads opened directly)."""
    from flask import abort, session

    if session.get("role") == "Admin":
        abort(403, description="QA (Admin) has no access to KPI Dashboard.")

MONTH_LABELS_EN = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

MONTH_KEY_PATTERN = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")

VALID_RANGES = set(RANGE_LABELS.keys())
EXPORT_RANGE = "month"  # a monthly snapshot represents the last 30 days


def _range_param():
    value = request.args.get("range", DEFAULT_RANGE)
    return value if value in VALID_RANGES else DEFAULT_RANGE


def _all_employees():
    return User.query.filter_by(role="Member").order_by(User.id).all()


def get_employees_for_export(range_key=EXPORT_RANGE):
    """Flat dicts (name/role/totalAssigned/...) for kpi_excel.py to write
    into .xlsx -- sourced from the real DB, not a static dummy list."""
    summaries = employee_list_summary(_all_employees(), range_key)
    return [
        {
            "name": s["name"],
            "role": s["role"],
            "totalAssigned": s["totalAssigned"],
            "completed": s["completed"],
            "pending": s["pending"],
            "overdue": s["overdue"],
            "avgResolutionDays": s["avgResolutionDays"],
        }
        for s in summaries
    ]


def _history_dir():
    path = os.path.join(current_app.instance_path, "kpi_history")
    os.makedirs(path, exist_ok=True)
    return path


SNAPSHOT_NAME_PATTERN = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])\.xlsx$")


def _snapshot_path(filename):
    """Absolute path of an archived snapshot inside kpi_history, or None
    if `filename` isn't a plain "YYYY-MM.xlsx" name (prevents path traversal)."""
    if not isinstance(filename, str) or not SNAPSHOT_NAME_PATTERN.match(filename):
        return None
    base = os.path.realpath(_history_dir())
    path = os.path.realpath(os.path.join(base, filename))
    if os.path.dirname(path) != base:
        return None
    return path


def _ensure_current_month_snapshot():
    """Rebuild (overwrite) THIS month's snapshot every time History is
    opened, so it stays current instead of freezing on day-1 data.
    Past months use a different filename and are never touched."""
    now = datetime.now()
    filename = f"{now.year}-{now.month:02d}.xlsx"
    filepath = _snapshot_path(filename)

    wb = build_individual_workbook(get_employees_for_export())
    wb.save(filepath)

    return filepath


# ==================== API: shared by Individual/Team panels & History ====================

@kpi_dashboard_bp.route("/api/employees")
def api_employees():
    """Employee summary list for a given range. Used by the Individual
    panel table (live) and the History Individual sub-panel."""
    range_key = _range_param()
    employees = _all_employees()
    summaries = employee_list_summary(employees, range_key)

    return jsonify(
        {
            "range": range_key,
            "rangeLabel": RANGE_LABELS[range_key],
            "ranges": [{"key": k, "label": v} for k, v in RANGE_LABELS.items()],
            "employees": summaries,
            "insights": employee_insights(summaries),
            "activeEmployeeId": employees[0].id if employees else None,
        }
    )


@kpi_dashboard_bp.route("/api/employees/<int:employee_id>")
def api_employee_detail(employee_id):
    """Single employee detail (stat card, trend chart, best practices)
    for a given range."""
    range_key = _range_param()
    employee = User.query.filter_by(id=employee_id, role="Member").first_or_404()
    return jsonify(employee_summary(employee, range_key))


@kpi_dashboard_bp.route("/api/team")
def api_team():
    """Team summary (totals, comparison chart, leaderboard) for a given
    range. Used by the Team panel (live) and History Team sub-panel."""
    range_key = _range_param()
    employees = _all_employees()
    return jsonify(team_summary(employees, range_key))


@kpi_dashboard_bp.route("/api/employees/<int:employee_id>/best-practices", methods=["GET"])
def api_list_best_practices(employee_id):
    """List of {id, note} for one Member. Used by the User Management
    edit-user panel; same ownership rule as the POST/DELETE endpoints."""
    from flask import session

    employee = User.query.filter_by(id=employee_id, role="Member").first_or_404()

    if session.get("role") == "Member" and session.get("user_id") != employee.id:
        return jsonify({"message": "Members can only view their own notes."}), 403
    if session.get("role") not in ("Super Admin", "Member"):
        return jsonify({"message": "Access denied."}), 403

    notes = [{"id": bp.id, "note": bp.note} for bp in employee.best_practices]
    return jsonify({"notes": notes})


@kpi_dashboard_bp.route("/api/employees/<int:employee_id>/best-practices", methods=["POST"])
def api_add_best_practice(employee_id):
    """Best Practice notes are written MANUALLY (never auto-generated
    from Issues). A Member may only add notes for themselves; Super
    Admin may add notes for anyone."""
    from flask import session

    employee = User.query.filter_by(id=employee_id, role="Member").first_or_404()

    if session.get("role") == "Member" and session.get("user_id") != employee.id:
        return jsonify({"message": "Members can only add notes for themselves."}), 403
    if session.get("role") not in ("Super Admin", "Member"):
        return jsonify({"message": "Access denied."}), 403

    # payload may not be a dict, and "note" may be non-string/null/missing
    payload = request.get_json(silent=True)
    note = payload.get("note") if isinstance(payload, dict) else None
    if not isinstance(note, str) or not note.strip():
        return jsonify({"message": "Note cannot be empty."}), 400
    note = note.strip()

    order = BestPractice.query.filter_by(user_id=employee.id).count()
    db.session.add(BestPractice(user_id=employee.id, note=note, sort_order=order))
    db.session.commit()

    return jsonify({"message": "Note added.", "note": note}), 201


@kpi_dashboard_bp.route("/api/employees/<int:employee_id>/best-practices/<int:note_id>", methods=["DELETE"])
def api_delete_best_practice(employee_id, note_id):
    """Same ownership rule as adding a note: a Member may only delete
    their own, Super Admin may delete anyone's."""
    from flask import session

    employee = User.query.filter_by(id=employee_id, role="Member").first_or_404()

    if session.get("role") == "Member" and session.get("user_id") != employee.id:
        return jsonify({"message": "Members can only delete their own notes."}), 403
    if session.get("role") not in ("Super Admin", "Member"):
        return jsonify({"message": "Access denied."}), 403

    note = BestPractice.query.filter_by(id=note_id, user_id=employee.id).first_or_404()
    db.session.delete(note)
    db.session.commit()

    return jsonify({"message": "Note deleted."})


# ==================== Export (per selected month) / History (.xlsx archive) ====================

XLSX_MIMETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _current_month_key():
    now = datetime.now()
    return f"{now.year}-{now.month:02d}"


def _month_param():
    """Validated "YYYY-MM" from ?month= (defaults to the current month).
    Returns None when the value is malformed, which also keeps arbitrary
    strings out of the archive file path."""
    value = (request.args.get("month") or _current_month_key()).strip()
    if value.endswith(".xlsx"):  # tolerate a snapshot filename
        value = value[: -len(".xlsx")]
    return value if MONTH_KEY_PATTERN.match(value) else None


def _employees_for_month(month_key):
    """Rows to export for one month.

    - Current month: live data from the DB, so the export is never stale.
    - Past months: the archived monthly snapshot (.xlsx) for that month.
    Returns None if there is no archive for that month."""
    if month_key == _current_month_key():
        return get_employees_for_export()

    filepath = _snapshot_path(f"{month_key}.xlsx")
    if filepath is None or not os.path.exists(filepath):
        return None
    return parse_employee_workbook(filepath)


def _export_month(xlsx_builder, pdf_builder_name, prefix):
    """Download the selected month as .xlsx (default) or .pdf (?format=pdf)."""
    month_key = _month_param()
    if month_key is None:
        return jsonify({"message": "Invalid month. Use the format YYYY-MM."}), 400

    export_format = (request.args.get("format") or "xlsx").strip().lower()
    if export_format not in ("xlsx", "pdf"):
        return jsonify({"message": "Invalid format. Use xlsx or pdf."}), 400

    try:
        employees = _employees_for_month(month_key)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"message": f"Failed to read the archive: {exc}"}), 400

    if employees is None:
        return jsonify({"message": "No archive found for the selected month."}), 404

    period_label = period_label_from_key(month_key)

    if export_format == "pdf":
        # Imported here so a missing `reportlab` only disables PDF export
        # instead of stopping the whole app from starting.
        try:
            from . import kpi_pdf
        except ImportError:
            return jsonify({
                "message": "PDF export needs the 'reportlab' package. Run: pip install -r requirements.txt",
            }), 500
        buffer = getattr(kpi_pdf, pdf_builder_name)(employees, period_label)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{prefix}-{month_key}.pdf",
            mimetype="application/pdf",
        )

    buffer = workbook_to_bytes(xlsx_builder(employees, period_label))
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{prefix}-{month_key}.xlsx",
        mimetype=XLSX_MIMETYPE,
    )


@kpi_dashboard_bp.route("/export/individual")
def export_individual():
    return _export_month(build_individual_workbook, "build_individual_pdf", "kpi-individual")


@kpi_dashboard_bp.route("/export/team")
def export_team():
    return _export_month(build_team_workbook, "build_team_pdf", "kpi-team")


@kpi_dashboard_bp.route("/history")
def history():
    _ensure_current_month_snapshot()

    snapshots = []
    for filename in sorted(os.listdir(_history_dir()), reverse=True):
        match = SNAPSHOT_NAME_PATTERN.match(filename)
        if not match:
            continue  # ignore any stray file in the archive folder
        year, month = match.groups()
        stat = os.stat(_snapshot_path(filename))

        snapshots.append(
            {
                "filename": filename,
                "label": f"{MONTH_LABELS_EN[int(month) - 1]} {year}",
                "createdAt": datetime.fromtimestamp(stat.st_mtime).strftime("%d %b %Y"),
                "sizeBytes": stat.st_size,
            }
        )

    return jsonify({"snapshots": snapshots})


@kpi_dashboard_bp.route("/history/data/<string:filename>")
def history_data(filename):
    """Read one archived monthly .xlsx snapshot back as JSON. Kept for
    audit/preview of old archives; the live History Individual/Team view
    now uses /api/* (direct DB data) to stay consistent with the live
    panels."""
    filepath = _snapshot_path(filename)
    if filepath is None or not os.path.exists(filepath):
        return jsonify({"message": "Snapshot not found."}), 404

    try:
        rows = parse_employee_workbook(filepath)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"message": f"Failed to read snapshot: {exc}"}), 400

    return jsonify({"employees": rows})
