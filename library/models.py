"""
Model SQLAlchemy untuk seluruh data RnD Portal.

PENTING (persiapan migrasi SQLite -> PostgreSQL):
- Semua kolom pakai tipe generik SQLAlchemy (Integer, String, Float, Date,
  DateTime, Text, Boolean). Tipe-tipe ini otomatis diterjemahkan ke tipe
  native masing-masing dialect oleh SQLAlchemy -- tidak ada fitur khusus
  SQLite yang dipakai (tidak ada kolom JSON blob, tidak ada raw SQL sqlite,
  tidak ada AUTOINCREMENT manual, dst).
- Data historis KPI disimpan sebagai baris-baris ternormalisasi
  (satu KPIRecord per employee per titik waktu), BUKAN sebagai satu kolom
  JSON list seperti array trend di JS versi lama. Ini sengaja supaya nanti
  gampang di-index & di-agregasi pakai SQL asli Postgres (GROUP BY, date
  range query, dst), bukan cuma dummy data yang ditulis ulang.
- Untuk pindah ke Postgres nanti: pasang `psycopg2-binary`, set env var
  DATABASE_URL ke `postgresql+psycopg2://user:pass@host:5432/db_name`,
  lalu jalankan ulang `db.create_all()` (atau pakai Flask-Migrate kalau
  proyek sudah butuh migration history). Tidak ada satupun kode di model
  ini yang perlu diubah.
"""

from library.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120), nullable=False)
    team = db.Column(db.String(80), nullable=False, default="General")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    kpi_records = db.relationship(
        "KPIRecord",
        backref="employee",
        cascade="all, delete-orphan",
        order_by="KPIRecord.period_date",
    )
    best_practices = db.relationship(
        "BestPractice",
        backref="employee",
        cascade="all, delete-orphan",
        order_by="BestPractice.sort_order",
    )

    def __repr__(self):
        return f"<Employee {self.name}>"


class KPIRecord(db.Model):
    """Satu baris = ringkasan kinerja karyawan pada satu titik waktu
    (mingguan). Tabel inilah yang menopang filter Recent / Last Week /
    Last Month / Last Year -- semuanya tinggal query
    `WHERE period_date >= cutoff`, tidak perlu struktur khusus per rentang.
    """

    __tablename__ = "kpi_records"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False, index=True)
    period_date = db.Column(db.Date, nullable=False, index=True)
    total_assigned = db.Column(db.Integer, nullable=False, default=0)
    completed = db.Column(db.Integer, nullable=False, default=0)
    pending = db.Column(db.Integer, nullable=False, default=0)
    overdue = db.Column(db.Integer, nullable=False, default=0)
    avg_resolution_days = db.Column(db.Float, nullable=False, default=0)

    def __repr__(self):
        return f"<KPIRecord emp={self.employee_id} {self.period_date}>"


class BestPractice(db.Model):
    __tablename__ = "best_practices"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False, index=True)
    note = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class Issue(db.Model):
    """Satu baris = satu issue yang didaftarkan lewat panel Issue Register.
    `image_filename` cuma nyimpen nama file -- file aslinya disimpan di
    static/assets/upload/ (lihat library/workspace/issue_monitor/routes.py),
    supaya DB tidak perlu nyimpen BLOB besar."""

    __tablename__ = "issues"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    category = db.Column(db.String(80), nullable=False)
    event = db.Column(db.String(80), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="Medium")
    status = db.Column(db.String(20), nullable=False, default="Open")
    deadline = db.Column(db.Date, nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    owner_name = db.Column(db.String(120), nullable=False, default="Admin")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        from flask import url_for

        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "event": self.event,
            "priority": self.priority,
            "status": self.status,
            "deadline": self.deadline.strftime("%d-%m-%Y") if self.deadline else None,
            "owner": self.owner_name,
            "image_url": (
                url_for("static", filename=f"assets/upload/{self.image_filename}")
                if self.image_filename
                else None
            ),
        }

    def __repr__(self):
        return f"<Issue {self.title}>"