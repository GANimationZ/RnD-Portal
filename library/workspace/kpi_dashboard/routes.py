"""KPI Dashboard blueprint.

- User (role="Member") + KPIRecord + BestPractice are the data source,
  portable across SQLite/PostgreSQL.
- All calculations (workload bar, completion rate, leaderboard, range
  aggregation) live in metrics.py -- these routes just query the DB and
  call metrics.py, returning ready-to-render JSON.
- /api/* is shared by the Individual/Team panels (live) and the History
  sub-panels, so Recent/Last Week/Last Month/Last Year stay consistent
  everywhere. Export/import/.xlsx snapshot history is a separate,
  archival-only feature.
"""

import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, send_file, send_from_directory

from library.auth import login_required
from library.extensions import db
from library.models import BestPractice, User

from .kpi_excel import (
    build_individual_workbook,
    build_team_workbook,
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
    endpoint can be added later without this protection."""
    from flask import jsonify, session

    if session.get("role") == "Admin":
        return jsonify({"message": "QA (Admin) tidak memiliki akses ke KPI Dashboard."}), 403

MONTH_LABELS_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]

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


def _ensure_current_month_snapshot():
    """Auto-generate this month's snapshot if it doesn't exist yet, in
    case nobody exported manually."""
    now = datetime.now()
    filename = f"{now.year}-{now.month:02d}.xlsx"
    filepath = os.path.join(_history_dir(), filename)

    if not os.path.exists(filepath):
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


@kpi_dashboard_bp.route("/api/employees/<int:employee_id>/best-practices", methods=["POST"])
def api_add_best_practice(employee_id):
    """Best Practice notes are written MANUALLY (never auto-generated
    from Issues). A Member may only add notes for themselves; Super
    Admin may add notes for anyone."""
    from flask import session

    employee = User.query.filter_by(id=employee_id, role="Member").first_or_404()

    if session.get("role") == "Member" and session.get("user_id") != employee.id:
        return jsonify({"message": "Member cuma bisa menambah catatan untuk dirinya sendiri."}), 403
    if session.get("role") not in ("Super Admin", "Member"):
        return jsonify({"message": "Akses ditolak."}), 403

    note = (request.get_json(silent=True) or {}).get("note", "").strip()
    if not note:
        return jsonify({"message": "Catatan tidak boleh kosong."}), 400

    order = BestPractice.query.filter_by(user_id=employee.id).count()
    db.session.add(BestPractice(user_id=employee.id, note=note, sort_order=order))
    db.session.commit()

    return jsonify({"message": "Catatan ditambahkan.", "note": note}), 201


# ==================== Export / Import / History (.xlsx archive) ====================

@kpi_dashboard_bp.route("/export/individual")
def export_individual():
    wb = build_individual_workbook(get_employees_for_export())
    buffer = workbook_to_bytes(wb)
    filename = f"kpi-individual-{datetime.now():%Y-%m-%d}.xlsx"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@kpi_dashboard_bp.route("/export/team")
def export_team():
    wb = build_team_workbook(get_employees_for_export())
    buffer = workbook_to_bytes(wb)
    filename = f"kpi-team-{datetime.now():%Y-%m-%d}.xlsx"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@kpi_dashboard_bp.route("/import", methods=["POST"])
def import_employees():
    file = request.files.get("file")
    if not file:
        return jsonify({"message": "File tidak ditemukan."}), 400

    try:
        rows = parse_employee_workbook(file.stream)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"message": f"Gagal membaca file: {exc}"}), 400

    # TODO: upsert `rows` into User/KPIRecord by name if Excel import is
    # meant to overwrite DB data (not just preview). For now this only
    # counts rows so the frontend can show a notification, as before.
    updated = len(rows)
    created = 0

    return jsonify({"updated": updated, "created": created, "rows": rows})


@kpi_dashboard_bp.route("/history")
def history():
    _ensure_current_month_snapshot()

    snapshots = []
    for filename in sorted(os.listdir(_history_dir()), reverse=True):
        if not filename.endswith(".xlsx"):
            continue
        year, month = filename.replace(".xlsx", "").split("-")
        filepath = os.path.join(_history_dir(), filename)
        stat = os.stat(filepath)

        snapshots.append(
            {
                "filename": filename,
                "label": f"{MONTH_LABELS_ID[int(month) - 1]} {year}",
                "createdAt": datetime.fromtimestamp(stat.st_mtime).strftime("%d %b %Y"),
                "sizeBytes": stat.st_size,
                "downloadUrl": f"/workspace/kpi-dashboard/history/download/{filename}",
            }
        )

    return jsonify({"snapshots": snapshots})


@kpi_dashboard_bp.route("/history/download/<path:filename>")
def download_history(filename):
    return send_from_directory(_history_dir(), filename, as_attachment=True)


@kpi_dashboard_bp.route("/history/data/<path:filename>")
def history_data(filename):
    """Read one archived monthly .xlsx snapshot back as JSON. Kept for
    audit/preview of old archives; the live History Individual/Team view
    now uses /api/* (direct DB data) to stay consistent with the live
    panels."""
    filepath = os.path.join(_history_dir(), filename)
    if not os.path.exists(filepath):
        return jsonify({"message": "Snapshot tidak ditemukan."}), 404

    try:
        rows = parse_employee_workbook(filepath)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"message": f"Gagal membaca snapshot: {exc}"}), 400

    return jsonify({"employees": rows})
