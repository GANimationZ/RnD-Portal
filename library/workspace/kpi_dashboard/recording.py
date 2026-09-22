"""
Penghubung Issue Monitor <-> KPI Dashboard (poin "hubungkan semuanya jadi
satu"): dulu KPIRecord cuma dummy data lepas, sekarang terisi OTOMATIS dari
aktivitas Issue asli.

Alur:
1. Issue dibuat dengan assignee (Member) -> record_assignment(): KPIRecord
   minggu berjalan milik Member itu, total_assigned +1, pending +1.
2. Issue ditandai Closed -> record_completion(): kalau issue itu belum
   pernah tercatat assigned (assignee baru ditentukan pas nutup, sesuai
   poin 4 -- "assign pelaksana di akhir"), assigned dicatat dulu baru
   completed; kalau sudah pernah assigned, tinggal pending -1 & completed
   +1, plus avg_resolution_days dihitung dari created_at -> sekarang.

Satu Member cuma punya SATU baris KPIRecord per minggu (lihat
UniqueConstraint di model) -- baris itu diakumulasi terus selama minggu
berjalan, bukan satu baris per issue.
"""

from datetime import date, datetime, timedelta

from library.extensions import db
from library.models import KPIRecord


def _week_start(day=None):
    """Senin di minggu yang sama dengan `day` (default hari ini) --
    dipakai sebagai `period_date` supaya satu minggu = satu baris."""
    day = day or date.today()
    return day - timedelta(days=day.weekday())


def _get_or_create_week_record(user_id, day=None):
    period_date = _week_start(day)
    record = KPIRecord.query.filter_by(user_id=user_id, period_date=period_date).first()
    if not record:
        record = KPIRecord(user_id=user_id, period_date=period_date)
        db.session.add(record)
        db.session.flush()
    return record


def record_assignment(user_id):
    """Dipanggil saat Issue baru dibuat/diberi assignee: nambah beban
    kerja Member itu di minggu berjalan."""
    if not user_id:
        return
    record = _get_or_create_week_record(user_id)
    record.total_assigned += 1
    record.pending += 1


def record_completion(user_id, created_at, already_assigned=True):
    """Dipanggil saat Issue ditandai Closed.

    `already_assigned=False` dipakai untuk kasus "assign pelaksana di
    akhir" (issue selesai duluan baru ditentukan siapa yang ngerjain) --
    di situ total_assigned juga perlu +1 karena belum pernah tercatat
    sebelumnya lewat record_assignment()."""
    if not user_id:
        return

    record = _get_or_create_week_record(user_id)
    if not already_assigned:
        record.total_assigned += 1
    else:
        record.pending = max(0, record.pending - 1)

    record.completed += 1

    if created_at:
        resolution_days = max(0.0, (datetime.utcnow() - created_at).total_seconds() / 86400)
        # Rata-rata berjalan sederhana: gabungkan resolusi baru ini dengan
        # rata-rata lama secara tertimbang jumlah completed sejauh ini.
        prior_completed = max(0, record.completed - 1)
        record.avg_resolution_days = round(
            ((record.avg_resolution_days * prior_completed) + resolution_days) / record.completed,
            2,
        )


def sync_overdue_flags():
    """Dipanggil ringan tiap kali /api/issues diakses: issue yang masih
    Open/Pending dan sudah lewat deadline dihitung `overdue` di KPIRecord
    minggu berjalan milik assignee-nya. Sengaja idempotent-safe dengan
    cara reset-lalu-hitung-ulang tiap panggilan, supaya tidak dobel-hitung."""
    from library.models import Issue

    overdue_issues = Issue.query.filter(
        Issue.status.in_(["Open", "Pending"]),
        Issue.deadline < date.today(),
        Issue.assignee_id.isnot(None),
    ).all()

    counts = {}
    for issue in overdue_issues:
        counts[issue.assignee_id] = counts.get(issue.assignee_id, 0) + 1

    this_week = _week_start()
    # Reset overdue minggu berjalan untuk semua Member yang punya baris,
    # baru diisi ulang dari hasil hitung -- jauh lebih murah daripada
    # nyimpen histori overdue per hari.
    for record in KPIRecord.query.filter_by(period_date=this_week).all():
        record.overdue = counts.get(record.user_id, 0)
