"""
Generator dummy data untuk KPI Dashboard & Issue Monitor.

Supaya app langsung ada isinya begitu database dibuat (baik masih SQLite
maupun setelah dipindah ke PostgreSQL), tanpa perlu isi manual. Semua
lewat model SQLAlchemy biasa, jadi tidak ada query/tipe data spesifik
SQLite yang perlu ditulis ulang saat migrasi -- lihat MIGRATION.md.

Cara pakai:
    from library.seed import seed_dummy_data
    with app.app_context():
        db.create_all()
        seed_dummy_data()   # idempotent -- no-op kalau data sudah ada
"""

import random
from datetime import date, timedelta

from library.extensions import db
from library.models import (
    BestPractice,
    Employee,
    Issue,
    KPIRecord,
    User,
    UserCategoryScope,
    UserEventScope,
)

# Akun demo untuk mencoba 3 level akses. Password sengaja dituliskan apa
# adanya di sini (bukan project production) supaya gampang dicoba pertama
# kali -- SEGERA ganti password ini via halaman User Management begitu
# sudah dipakai beneran.
USER_SEED = [
    {
        "username": "superadmin", "email": "superadmin@rndportal.local",
        "password": "SuperAdmin123", "role": "Super Admin",
        "categories": [], "events": [],
    },
    {
        "username": "qa.admin", "email": "qa.admin@rndportal.local",
        "password": "AdminQA12345", "role": "Admin",
        "categories": [], "events": [],
    },
    {
        # Member ini muncul di combobox assignee kalau QA bikin issue
        # category "PCBA/SMT" ATAU "SQA", event "PV" ATAU "MP".
        "username": "budi.santoso", "email": "budi.santoso@rndportal.local",
        "password": "MemberBudi12", "role": "Member",
        "categories": ["PCBA/SMT", "SQA"], "events": ["PV", "MP"],
    },
    {
        # Member ini cuma muncul untuk category "Line-Prod" & event "Pre-MP".
        "username": "sinta.wijaya", "email": "sinta.wijaya@rndportal.local",
        "password": "MemberSinta12", "role": "Member",
        "categories": ["Line-Prod"], "events": ["Pre-MP"],
    },
    {
        "username": "dimas.pratama", "email": "dimas.pratama@rndportal.local",
        "password": "MemberDimas12", "role": "Member",
        "categories": ["OQA", "CSS/SVC"], "events": ["MP", "Field"],
    },
]

EMPLOYEE_SEED = [
    {
        "name": "Rani Freya", "role": "PCBA Engineer", "team": "PCBA/SMT",
        "base_assigned": 5, "base_completed": 3, "base_avg_days": 2.4,
        "best_practices": [
            "Selalu verifikasi root cause sebelum menutup issue.",
            "Update status issue maksimal H+1 setelah ada perkembangan.",
            "Gunakan template laporan standar untuk kategori PCBA/SMT.",
        ],
    },
    {
        "name": "Dimas Pratama", "role": "Assembly Lead", "team": "Line-Prod",
        "base_assigned": 4, "base_completed": 2, "base_avg_days": 3.1,
        "best_practices": [
            "Koordinasi dengan QA sebelum eskalasi issue assembly.",
            "Dokumentasikan foto sebelum/sesudah perbaikan.",
        ],
    },
    {
        "name": "Sinta Wijaya", "role": "QA Inspector", "team": "SQA",
        "base_assigned": 3, "base_completed": 2, "base_avg_days": 1.8,
        "best_practices": [
            "Prioritaskan issue kategori High sebelum jam 10 pagi.",
            "Selalu cross-check dengan checklist QA sebelum status Closed.",
        ],
    },
]

# ~1 tahun lebih dikit (mingguan) supaya filter "Last Year" punya data penuh.
WEEKS_OF_HISTORY = 56

# Deadline disebar relatif ke tanggal seeding (bukan tanggal tetap) supaya
# Priority Matrix tetap relevan kapan pun database ini dibuat ulang.
ISSUE_SEED = [
    {"title": "Check Quality, Module gone wrong", "description": "Modul hasil PV menunjukkan hasil yang tidak konsisten.", "priority": "High", "category": "PCBA/SMT", "event": "PV", "days_offset": 2, "owner_name": "Admin", "status": "Pending"},
    {"title": "Firmware crash on boot sequence", "description": "Unit tidak bisa boot setelah update firmware terbaru.", "priority": "High", "category": "SQA", "event": "MP", "days_offset": -2, "owner_name": "Rani Freya", "status": "Open"},
    {"title": "Intermittent connector wobble", "description": "Konektor longgar secara acak saat uji getar.", "priority": "Medium", "category": "Line-Prod", "event": "PV", "days_offset": 1, "owner_name": "Dimas Pratama", "status": "Open"},
    {"title": "Assembly misalignment on tray B", "description": "Posisi komponen di tray B bergeser dari spek.", "priority": "Medium", "category": "OQA", "event": "PV", "days_offset": 19, "owner_name": "Dimas Pratama", "status": "Open"},
    {"title": "Mainboard short circuit at test bench", "description": "Ditemukan short di mainboard saat pengujian akhir.", "priority": "High", "category": "SQA", "event": "Field", "days_offset": 34, "owner_name": "Admin", "status": "Pending"},
    {"title": "Minor cosmetic scratch on casing", "description": "Goresan kecil di casing, tidak mempengaruhi fungsi.", "priority": "Low", "category": "OQA", "event": "MP", "days_offset": 3, "owner_name": "Sinta Wijaya", "status": "Open"},
    {"title": "Update test jig calibration schedule", "description": "Jadwal kalibrasi jig perlu diperbarui.", "priority": "Low", "category": "Line-Prod", "event": "Pre-MP", "days_offset": 75, "owner_name": "Sinta Wijaya", "status": "Open"},
    {"title": "Packaging label misprint batch 12", "description": "Label kemasan batch 12 salah cetak, sudah diperbaiki.", "priority": "Low", "category": "Line-Prod", "event": "MP", "days_offset": -25, "owner_name": "Sinta Wijaya", "status": "Closed"},
]


def seed_issues():
    if Issue.query.first():
        return

    today = date.today()
    for spec in ISSUE_SEED:
        db.session.add(
            Issue(
                title=spec["title"],
                description=spec["description"],
                priority=spec["priority"],
                category=spec["category"],
                event=spec["event"],
                deadline=today + timedelta(days=spec["days_offset"]),
                owner_name=spec["owner_name"],
                status=spec["status"],
            )
        )
    db.session.commit()


def seed_employees():
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


def seed_users():
    if User.query.first():
        return

    for spec in USER_SEED:
        user = User(username=spec["username"], email=spec["email"], role=spec["role"])
        user.set_password(spec["password"])
        db.session.add(user)
        db.session.flush()  # supaya user.id kebentuk sebelum insert scope

        for category in spec["categories"]:
            db.session.add(UserCategoryScope(user_id=user.id, category=category))
        for event in spec["events"]:
            db.session.add(UserEventScope(user_id=user.id, event=event))

    db.session.commit()


def seed_dummy_data():
    """Idempotent: tiap fungsi cek tabelnya sendiri, aman dipanggil setiap
    kali aplikasi start."""
    seed_users()
    seed_employees()
    seed_issues()
