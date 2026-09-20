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

    db.session.commit()