"""SQLAlchemy models for RnD Portal.

Notes:
- All columns use generic SQLAlchemy types (Integer, String, Float, Date,
  DateTime, Text, Boolean) so nothing here needs to change when migrating
  from SQLite to PostgreSQL -- just set DATABASE_URL (see MIGRATION.md).
- Historical KPI data is stored as normalized rows (one KPIRecord per user
  per period), not as a JSON blob, so it stays queryable/indexable in
  Postgres.
- Single team, three access levels via User.role: "Super Admin" (manages
  users), "Admin" (QA, creates/closes issues), "Member" (view issues,
  execute assigned ones). See library/auth.py:roles_required().
- UserCategoryScope / UserEventScope are normalized pivot tables so a
  Member can have more than one category/event.
"""

from library.extensions import db

ROLE_CHOICES = ["Super Admin", "Admin", "Member"]

# Must match Issue.category / Issue.event and issue-monitor.js's
# CATEGORY_META / EVENT_META exactly, so Member <-> Issue scope matching
# stays correct.
CATEGORY_CHOICES = ["PCBA/SMT", "SQA", "Line-Prod", "OQA", "CSS/SVC"]
EVENT_CHOICES = ["PV", "Pre-MP", "MP", "Field"]


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="Member")
    job_title = db.Column(db.String(120), nullable=True)  # cosmetic label for KPI Dashboard
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    approved_at = db.Column(db.DateTime, nullable=True)
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
        """True if this user's scope includes both category and event --
        the requirement to appear in the Issue Register assignee combobox."""
        return category in self.categories and event in self.events

    @property
    def status_label(self):
        if self.is_active:
            return "Active"
        return "Pending" if self.approved_at is None else "Inactive"

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "status_label": self.status_label,
            "categories": self.categories,
            "events": self.events,
            "created_at": self.created_at.strftime("%d-%m-%Y") if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class UserCategoryScope(db.Model):
    """One row = one category a user may handle. Multiple rows per user_id
    means more than one category."""

    __tablename__ = "user_category_scopes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category = db.Column(db.String(80), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "category", name="uq_user_category_scope"),
    )


class UserEventScope(db.Model):
    """Same as UserCategoryScope, for Event."""

    __tablename__ = "user_event_scopes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    event = db.Column(db.String(80), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "event", name="uq_user_event_scope"),
    )


class KPIRecord(db.Model):
    """One row = a Member's performance summary for one week. Backs the
    Recent / Last Week / Last Month / Last Year filters via a simple
    `WHERE period_date >= cutoff` query.

    Filled automatically from Issue Monitor activity (see recording.py):
    - Issue created with an assignee -> total_assigned & pending +1.
    - Issue closed -> completed +1, pending -1, avg_resolution_days updated.
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
    """A manually-written tip for a Member (by themselves or Super Admin),
    not auto-generated from Issue activity."""

    __tablename__ = "best_practices"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    note = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Issue(db.Model):
    """One row = one issue registered via Issue Register.

    `owner_name` = the QA/Admin who created the issue.
    `assignee_id` = the Member assigned to execute it (chosen from a
    combobox filtered by category/event, see User.covers()).
    """

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
                url_for("static", filename=f"assets/uploads/issues/{self.image_filename}")
                if self.image_filename
                else None
            ),
            "attachments": [a.to_dict() for a in self.attachments],
        }

    def __repr__(self):
        return f"<Issue {self.title}>"


class IssueAttachment(db.Model):
    """One file attached to an Issue (image, Word, Excel, or PowerPoint).
    Kept separate from Issue.image_filename (retained for backward
    compatibility) so an issue can have multiple attachments."""

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
            "url": url_for("static", filename=f"assets/uploads/issues/{self.filename}"),
        }


class TvDesignAsset(db.Model):
    """One board/product design entry in the TV Design Concept library.
    Searchable by serial_number, production, and origin."""

    __tablename__ = "tv_design_assets"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    serial_number = db.Column(db.String(120), nullable=False, index=True)
    production = db.Column(db.String(120), nullable=True, index=True)
    origin = db.Column(db.String(120), nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    attachments = db.relationship(
        "TvDesignAttachment", backref="asset", cascade="all, delete-orphan",
        order_by="TvDesignAttachment.id",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "serial_number": self.serial_number,
            "production": self.production,
            "origin": self.origin,
            "notes": self.notes,
            "created_by": self.created_by.username if self.created_by else None,
            "created_at": self.created_at.strftime("%d-%m-%Y") if self.created_at else None,
            "attachments": [a.to_dict() for a in self.attachments],
        }

    def __repr__(self):
        return f"<TvDesignAsset {self.serial_number}>"


class TvDesignAttachment(db.Model):
    """One file (image / excel / ppt / pdf) attached to a TvDesignAsset."""

    __tablename__ = "tv_design_attachments"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("tv_design_assets.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), nullable=False, default="other")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        from flask import url_for

        return {
            "id": self.id,
            "name": self.original_name,
            "type": self.file_type,
            "url": url_for("static", filename=f"assets/uploads/tv-design/{self.filename}"),
        }
