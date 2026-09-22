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

MANAJEMEN USER & HAK AKSES (ditambahkan bareng fitur User Management):
- Cuma ADA SATU team dengan 3 level akses (User.role): "Super Admin" (dev,
  mengelola user), "Admin" (QA, membuat & menutup issue), "Member" (cuma
  bisa melihat issue). Lihat library/auth.py:roles_required().
- UserCategoryScope & UserEventScope = tabel pivot ternormalisasi (bukan
  CSV/JSON di satu kolom, konsisten dengan filosofi KPIRecord di atas).
  Satu Member bisa punya BANYAK baris category & BANYAK baris event --
  itulah yang bikin "kategori/event bisa lebih dari 1 per orang".
- Issue.assignee_id menunjuk ke User (Member) yang ditugaskan mengerjakan
  issue tsb -- terpisah dari owner_name (yang membuat issue/QA-nya).
"""

from library.extensions import db

ROLE_CHOICES = ["Super Admin", "Admin", "Member"]

# Sengaja disamakan PERSIS dengan string yang sudah dipakai Issue.category /
# Issue.event & static/javascript/workspace/issue-monitor.js (CATEGORY_META /
# EVENT_META) supaya pencocokan scope Member <-> Issue tidak meleset.
CATEGORY_CHOICES = ["PCBA/SMT", "SQA", "Line-Prod", "OQA", "CSS/SVC"]
EVENT_CHOICES = ["PV", "Pre-MP", "MP", "Field"]


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="Member")
    # Judul/jabatan bebas buat tampilan KPI Dashboard (mis. "PCBA Engineer") --
    # murni kosmetik, tidak dipakai buat otorisasi (itu urusan `role`).
    job_title = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    category_scopes = db.relationship(
        "UserCategoryScope", backref="user", cascade="all, delete-orphan"
    )
    event_scopes = db.relationship(
        "UserEventScope", backref="user", cascade="all, delete-orphan"
    )
    kpi_records = db.relationship(
        "KPIRecord", backref="user", cascade="all, delete-orphan",
        order_by="KPIRecord.period_date",
    )
    best_practices = db.relationship(
        "BestPractice", backref="user", cascade="all, delete-orphan",
        order_by="BestPractice.sort_order",
    )

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    @property
    def categories(self):
        return sorted(s.category for s in self.category_scopes)

    @property
    def events(self):
        return sorted(s.event for s in self.event_scopes)

    def covers(self, category, event):
        """True kalau user ini (biasanya Member) di-scope ke KEDUA
        category & event tsb -- inilah syarat muncul di combobox assignee
        Issue Register."""
        return category in self.categories and event in self.events

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "categories": self.categories,
            "events": self.events,
            "created_at": self.created_at.strftime("%d-%m-%Y") if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class UserCategoryScope(db.Model):
    """Satu baris = satu kategori yang boleh ditangani seorang user.
    Banyak baris per user_id = boleh lebih dari satu kategori."""

    __tablename__ = "user_category_scopes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category = db.Column(db.String(80), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "category", name="uq_user_category_scope"),
    )


class UserEventScope(db.Model):
    """Sama seperti UserCategoryScope, tapi untuk Event."""

    __tablename__ = "user_event_scopes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    event = db.Column(db.String(80), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "event", name="uq_user_event_scope"),
    )


class KPIRecord(db.Model):
    """Satu baris = ringkasan kinerja seorang Member pada satu titik waktu
    (mingguan). Tabel inilah yang menopang filter Recent / Last Week /
    Last Month / Last Year -- semuanya tinggal query
    `WHERE period_date >= cutoff`, tidak perlu struktur khusus per rentang.

    Diisi OTOMATIS oleh Issue Monitor (bukan data dummy lagi):
    - Issue baru dibuat dengan assignee -> total_assigned & pending +1
      untuk Member itu di minggu berjalan.
    - Issue ditandai Closed (assignee sudah/baru ditentukan saat itu) ->
      completed +1, pending -1, avg_resolution_days dihitung ulang.
    Lihat library/workspace/kpi_dashboard/recording.py.
    """

    __tablename__ = "kpi_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    period_date = db.Column(db.Date, nullable=False, index=True)
    total_assigned = db.Column(db.Integer, nullable=False, default=0)
    completed = db.Column(db.Integer, nullable=False, default=0)
    pending = db.Column(db.Integer, nullable=False, default=0)
    overdue = db.Column(db.Integer, nullable=False, default=0)
    avg_resolution_days = db.Column(db.Float, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("user_id", "period_date", name="uq_kpi_record_week"),
    )

    def __repr__(self):
        return f"<KPIRecord user={self.user_id} {self.period_date}>"


class BestPractice(db.Model):
    """Catatan praktik-baik per Member -- ditulis manual (oleh Member
    sendiri atau Super Admin), BUKAN digenerate otomatis dari Issue.
    Lihat library/workspace/kpi_dashboard/routes.py -> api_add_best_practice."""

    __tablename__ = "best_practices"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    note = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Issue(db.Model):
    """Satu baris = satu issue yang didaftarkan lewat panel Issue Register.
    `image_filename` cuma nyimpen nama file -- file aslinya disimpan di
    static/assets/upload/ (lihat library/workspace/issue_monitor/routes.py),
    supaya DB tidak perlu nyimpen BLOB besar.

    `owner_name` = nama QA/Admin yang MENDAFTARKAN issue (siapa yang bikin).
    `assignee_id` = User (role Member) yang DITUGASKAN MENGERJAKAN issue,
    dipilih lewat combobox di form Register yang otomatis difilter sesuai
    category & event issue ini (lihat User.covers() di models.py &
    library/admin/user_management/routes.py:api_assignable_users)."""

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
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    closed_at = db.Column(db.DateTime, nullable=True)

    assignee = db.relationship("User", foreign_keys=[assignee_id])
    attachments = db.relationship(
        "IssueAttachment", backref="issue", cascade="all, delete-orphan",
        order_by="IssueAttachment.id",
    )

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
            "created_at": self.created_at.strftime("%d-%m-%Y") if self.created_at else None,
            "owner": self.owner_name,
            "assignee_id": self.assignee_id,
            "assignee_name": self.assignee.username if self.assignee else None,
            "image_url": (
                url_for("static", filename=f"assets/upload/{self.image_filename}")
                if self.image_filename
                else None
            ),
            "attachments": [a.to_dict() for a in self.attachments],
        }

    def __repr__(self):
        return f"<Issue {self.title}>"


class IssueAttachment(db.Model):
    """Satu baris = satu file lampiran (bisa gambar, Word, Excel, atau
    PowerPoint) untuk sebuah Issue -- sengaja dipisah dari
    Issue.image_filename (yang dipertahankan untuk kompatibilitas gambar
    lama) supaya satu Issue bisa punya BANYAK lampiran sekaligus."""

    __tablename__ = "issue_attachments"

    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey("issues.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), nullable=False, default="other")  # image/word/excel/ppt/pdf/other
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        from flask import url_for

        return {
            "id": self.id,
            "name": self.original_name,
            "type": self.file_type,
            "url": url_for("static", filename=f"assets/upload/{self.filename}"),
        }