"""
Flask blueprint KPI Dashboard.

Alur data (setelah perombakan):
- Employee / KPIRecord / BestPractice (lihat library/models.py) adalah
  sumber data utama, sudah portable SQLite <-> PostgreSQL (poin 1).
- Semua kalkulasi (workload bar, completion rate, leaderboard, agregasi
  per rentang waktu) ada di metrics.py, bukan lagi di kpi-dashboard.js
  (poin 4). Endpoint di bawah cuma query DB lalu memanggil metrics.py,
  hasilnya langsung JSON siap-render.
- Endpoint /api/* dipakai BERSAMA oleh panel Individual & Team (live) dan
  sub-panel History (Individual/Team), supaya tampilan & filter
  Recent/Last Week/Last Month/Last Year konsisten di semua tempat
  (poin 2 & 3). Fitur export/import/snapshot .xlsx tetap ada terpisah,
  khusus untuk kebutuhan arsip dokumen bulanan.
"""

import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, send_file, send_from_directory

from library.auth import login_required, roles_required
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
    """Poin 1: QA (role "Admin") TIDAK boleh melihat KPI Dashboard sama
    sekali -- baik halaman maupun API-nya. Dipasang sebagai before_request
    (bukan decorator di tiap route satu-satu) supaya tidak ada endpoint
    yang kelewat, sesuai pelajaran dari bug blueprint-lupa-diproteksi
    sebelumnya."""
    from flask import jsonify, session

    if session.get("role") == "Admin":
        return jsonify({"message": "QA (Admin) tidak memiliki akses ke KPI Dashboard."}), 403

MONTH_LABELS_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]

VALID_RANGES = set(RANGE_LABELS.keys())
EXPORT_RANGE = "month"  # snapshot bulanan merepresentasikan data 30 hari terakhir


def _range_param():
    value = request.args.get("range", DEFAULT_RANGE)
    return value if value in VALID_RANGES else DEFAULT_RANGE


def _all_employees():
    return User.query.filter_by(role="Member").order_by(User.id).all()


def get_employees_for_export(range_key=EXPORT_RANGE):
    """Bentuk dict rata (name/role/totalAssigned/...) yang dipakai
    kpi_excel.py untuk nulis file .xlsx -- sumbernya sekarang DB asli,
    bukan dummy list statis lagi."""
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
    """Kalau snapshot bulan ini belum ada, generate otomatis (berjaga-jaga
    kalau user lupa export manual bulan ini)."""
    now = datetime.now()
    filename = f"{now.year}-{now.month:02d}.xlsx"
    filepath = os.path.join(_history_dir(), filename)

    if not os.path.exists(filepath):
        wb = build_individual_workbook(get_employees_for_export())
        wb.save(filepath)

    return filepath


# ==================== API: dipakai panel Individual/Team & History ====================

@kpi_dashboard_bp.route("/api/employees")
def api_employees():
    """Daftar ringkas semua karyawan untuk rentang waktu tertentu.
    Dipakai tabel di panel Individual (live) & sub-panel History Individual."""
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
    """Detail 1 karyawan (stat card, trend chart, best practices) untuk
    rentang waktu tertentu."""
    range_key = _range_param()
    employee = User.query.filter_by(id=employee_id, role="Member").first_or_404()
    return jsonify(employee_summary(employee, range_key))


@kpi_dashboard_bp.route("/api/team")
def api_team():
    """Ringkasan tim (totals, chart perbandingan, leaderboard) untuk
    rentang waktu tertentu. Dipakai panel Team (live) & sub-panel
    History Team."""
    range_key = _range_param()
    employees = _all_employees()
    return jsonify(team_summary(employees, range_key))


@kpi_dashboard_bp.route("/api/employees/<int:employee_id>/best-practices", methods=["POST"])
def api_add_best_practice(employee_id):
    """Best Practice = catatan yang DITULIS MANUAL (bukan digenerate
    otomatis dari Issue), supaya isinya benar-benar wawasan/tips yang
    disengaja dibagikan. Member cuma boleh menambah catatan untuk dirinya
    sendiri; Super Admin boleh menambah untuk siapa saja."""
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


# ==================== Export / Import / History (arsip .xlsx) ====================

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

    # TODO: upsert `rows` ke tabel Employee/KPIRecord berdasarkan nama kalau
    # nanti import Excel memang dimaksudkan untuk menimpa data DB (bukan
    # cuma preview). Untuk sekarang cuma dihitung supaya frontend bisa
    # tampilkan notifikasi, seperti versi sebelumnya.
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
    """Baca isi satu snapshot bulanan (.xlsx arsip) dan kembalikan sebagai
    JSON. Dipertahankan untuk kebutuhan audit/preview arsip lama; tampilan
    utama History Individual/Team sekarang memakai /api/* (data DB
    langsung) supaya konsisten dengan panel live."""
    filepath = os.path.join(_history_dir(), filename)
    if not os.path.exists(filepath):
        return jsonify({"message": "Snapshot tidak ditemukan."}), 404

    try:
        rows = parse_employee_workbook(filepath)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"message": f"Gagal membaca snapshot: {exc}"}), 400

    return jsonify({"employees": rows})
