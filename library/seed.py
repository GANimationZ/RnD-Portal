"""
Generator dummy data untuk persiapan Database KPI Dashboard.

Tujuan file ini (poin 1 permintaan perombakan):
- Supaya app langsung ada isinya begitu database dibuat (baik masih pakai
  SQLite maupun setelah dipindah ke PostgreSQL), tanpa perlu isi manual.
- Karena datanya masuk lewat model SQLAlchemy biasa (Employee / KPIRecord /
  BestPractice), proses migrasi SQLite -> PostgreSQL jadi tinggal ganti
  SQLALCHEMY_DATABASE_URI lalu jalankan seeder ini lagi -- tidak ada query
  atau tipe data yang spesifik-SQLite yang perlu ditulis ulang.

Cara pakai:
    from library.seed import seed_dummy_data
    with app.app_context():
        db.create_all()
        seed_dummy_data()   # no-op kalau data sudah ada
"""

import random
from datetime import date, timedelta

from library.extensions import db
from library.models import Employee, KPIRecord, BestPractice, Issue

EMPLOYEE_SEED = [
    {
        "name": "Kontolodon",
        "role": "PCBA Engineer",
        "team": "PCBA/SMT",
        "base_assigned": 5,
        "base_completed": 3,
        "base_avg_days": 2.4,
        "best_practices": [
            "Selalu verifikasi root cause sebelum menutup issue.",
            "Update status issue maksimal H+1 setelah ada perkembangan.",
            "Gunakan template laporan standar untuk kategori PCBA/SMT.",
        ],
    },
    {
        "name": "Dimas Pratamax",
        "role": "Assembly Lead",
        "team": "Line-Prod",
        "base_assigned": 4,
        "base_completed": 2,
        "base_avg_days": 3.1,
        "best_practices": [
            "Koordinasi dengan QA sebelum eskalasi issue assembly.",
            "Dokumentasikan foto sebelum/sesudah perbaikan.",
        ],
    },
    {
        "name": "Sinta Wijaya",
        "role": "QA Inspector",
        "team": "SQA",
        "base_assigned": 3,
        "base_completed": 2,
        "base_avg_days": 1.8,
        "best_practices": [
            "Prioritaskan issue kategori High sebelum jam 10 pagi.",
            "Selalu cross-check dengan checklist QA sebelum status Closed.",
        ],
    },
]

# ~1 tahun lebih dikit (mingguan) supaya filter "Last Year" punya data penuh.
WEEKS_OF_HISTORY = 56


def seed_dummy_data():
    """Idempotent: tidak melakukan apa-apa kalau tabel employees sudah terisi,
    jadi aman dipanggil setiap kali aplikasi start."""
    if Employee.query.first():
        return

    random.seed(42)  # dummy data konsisten tiap kali re-seed dari nol
    today = date.today()

    for spec in EMPLOYEE_SEED:
        employee = Employee(name=spec["name"], role=spec["role"], team=spec["team"])
        db.session.add(employee)
        db.session.flush()  # supaya employee.id kebentuk tanpa commit dulu

        for order, note in enumerate(spec["best_practices"]):
            db.session.add(BestPractice(employee_id=employee.id, note=note, sort_order=order))

        # Titik data mingguan dari yang paling lama ke yang paling baru.
        for week_index in range(WEEKS_OF_HISTORY, -1, -1):
            period_date = today - timedelta(weeks=week_index)
            noise = random.randint(-2, 3)

            assigned = max(1, spec["base_assigned"] + noise)
            completed = max(0, min(assigned, spec["base_completed"] + random.randint(-1, 2)))
            remaining = assigned - completed
            overdue = random.randint(0, max(0, remaining // 2))
            pending = max(0, remaining - overdue)
            avg_days = round(max(0.5, spec["base_avg_days"] + random.uniform(-0.6, 0.6)), 1)

            db.session.add(
                KPIRecord(
                    employee_id=employee.id,
                    period_date=period_date,
                    total_assigned=assigned,
                    completed=completed,
                    pending=pending,
                    overdue=overdue,
                    avg_resolution_days=avg_days,
                )
            )

    db.session.commit()


ISSUE_SEED = [
    {"title": "Check Quality, Module gone wrong", "category": "PCBA/SMT", "event": "PV", "priority": "High", "status": "Pending", "deadline": date(2026, 9, 18), "owner_name": "Admin"},
    {"title": "Firmware crash on boot sequence", "category": "SQA", "event": "MP", "priority": "High", "status": "Open", "deadline": date(2026, 9, 14), "owner_name": "Rani"},
    {"title": "Intermittent connector wobble", "category": "Line-Prod", "event": "PV", "priority": "Medium", "status": "Open", "deadline": date(2026, 9, 17), "owner_name": "Dimas"},
    {"title": "Assembly misalignment on tray B", "category": "OQA", "event": "PV", "priority": "Medium", "status": "Open", "deadline": date(2026, 10, 5), "owner_name": "Dimas"},
    {"title": "Mainboard short circuit at test bench", "category": "SQA", "event": "Field", "priority": "High", "status": "Pending", "deadline": date(2026, 10, 20), "owner_name": "Admin"},
    {"title": "Minor cosmetic scratch on casing", "category": "OQA", "event": "MP", "priority": "Low", "status": "Open", "deadline": date(2026, 9, 19), "owner_name": "Sinta"},
    {"title": "Update test jig calibration schedule", "category": "Line-Prod", "event": "Pre-MP", "priority": "Low", "status": "Open", "deadline": date(2026, 11, 30), "owner_name": "Sinta"},
    {"title": "Packaging label misprint batch 12", "category": "Line-Prod", "event": "MP", "priority": "Low", "status": "Closed", "deadline": date(2026, 8, 22), "owner_name": "Sinta"},
]


def seed_dummy_issues():
    """Idempotent, sama kayak seed_dummy_data: no-op kalau tabel issues
    sudah terisi. Deskripsi sengaja "-" -- dummy data lama tidak punya
    field deskripsi, jadi ini cuma placeholder."""
    if Issue.query.first():
        return

    for spec in ISSUE_SEED:
        db.session.add(Issue(description="-", **spec))

    db.session.commit()