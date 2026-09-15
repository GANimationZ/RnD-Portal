"""
Contoh Flask blueprint untuk KPI Dashboard: export/import pakai openpyxl
(gantikan SheetJS) + fitur History (snapshot Excel bulanan otomatis).

Cara pakai:
1. Taruh file ini di package Flask kamu (mis. app/workspace/kpi_dashboard.py),
   sesuaikan import `kpi_excel` dengan lokasi modulnya.
2. Ganti `get_employees()` supaya ambil dari model/DB asli (SQLite/Postgres),
   bukan dummy list di bawah.
3. Daftarkan blueprint ini di app factory: app.register_blueprint(kpi_dashboard_bp)
4. Endpoint `url_for('kpi_dashboard.export_individual')` dkk di template
   kpi-dashboard-index.html akan otomatis terhubung ke sini asal nama
   blueprint-nya "kpi_dashboard" (baris terakhir file ini).

Struktur folder riwayat: instance/kpi_history/YYYY-MM.xlsx
(satu file per bulan, dibuat otomatis kalau belum ada saat /history diakses).
"""

import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, send_file, send_from_directory

from .kpi_excel import (
    build_individual_workbook,
    build_team_workbook,
    workbook_to_bytes,
    parse_employee_workbook,
)

kpi_dashboard_bp = Blueprint("kpi_dashboard", __name__, url_prefix="/workspace/kpi-dashboard")

MONTH_LABELS_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def get_employees():
    """GANTI dengan query ke DB asli. Untuk sekarang masih dummy,
    sama seperti employeeData di kpi-dashboard.js."""
    return [
        {"name": "Rani Freya", "role": "PCBA Engineer", "totalAssigned": 18,
         "completed": 12, "pending": 4, "overdue": 2, "avgResolutionDays": 2.4},
        {"name": "Dimas Pratama", "role": "Assembly Lead", "totalAssigned": 14,
         "completed": 9, "pending": 3, "overdue": 2, "avgResolutionDays": 3.1},
        {"name": "Sinta Wijaya", "role": "QA Inspector", "totalAssigned": 10,
         "completed": 7, "pending": 2, "overdue": 1, "avgResolutionDays": 1.8},
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
        wb = build_individual_workbook(get_employees())
        wb.save(filepath)

    return filepath


@kpi_dashboard_bp.route("/export/individual")
def export_individual():
    wb = build_individual_workbook(get_employees())
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
    wb = build_team_workbook(get_employees())
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

    # TODO: simpan `rows` ke DB asli (upsert berdasarkan nama, mirip
    # applyImportedRows() versi lama di kpi-dashboard.js). Untuk sekarang
    # cuma dihitung supaya frontend bisa tampilkan notifikasi.
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

        snapshots.append({
            "filename": filename,
            "label": f"{MONTH_LABELS_ID[int(month) - 1]} {year}",
            "createdAt": datetime.fromtimestamp(stat.st_mtime).strftime("%d %b %Y"),
            "sizeBytes": stat.st_size,
            "downloadUrl": f"/workspace/kpi-dashboard/history/download/{filename}",
        })

    return jsonify({"snapshots": snapshots})


@kpi_dashboard_bp.route("/history/download/<path:filename>")
def download_history(filename):
    return send_from_directory(_history_dir(), filename, as_attachment=True)


@kpi_dashboard_bp.route("/history/data/<path:filename>")
def history_data(filename):
    """Baca isi satu snapshot bulanan dan kembalikan sebagai JSON, supaya
    frontend bisa render tabel/chart langsung di panel History (bukan cuma
    link download)."""
    filepath = os.path.join(_history_dir(), filename)
    if not os.path.exists(filepath):
        return jsonify({"message": "Snapshot tidak ditemukan."}), 404

    try:
        rows = parse_employee_workbook(filepath)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"message": f"Gagal membaca snapshot: {exc}"}), 400

    return jsonify({"employees": rows})