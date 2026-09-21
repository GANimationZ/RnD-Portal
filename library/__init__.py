"""
Application factory -- cara standar Flask merakit aplikasi (lihat
flask.palletsprojects.com/en/latest/patterns/appfactory/).

Kenapa dipindah ke sini (bug yang baru diperbaiki): sebelumnya
`app = Flask(__name__)` dibuat langsung di app.py, lalu blueprint
di-import & di-register sebagai baris terpisah di antara puluhan baris
route lain. Baris registrasi itu KEHAPUS/TERLEWAT saat refactor, hasilnya
blueprint kpi_dashboard & issue_monitor tidak pernah aktif walau
file route-nya sendiri tidak error (makanya errornya baru muncul di
runtime sebagai BuildError, bukan di saat start server).

Dengan create_app(), init db + register semua blueprint jadi SATU alur
wajib yang jelas urutannya, tidak mungkin lupa satu tanpa ketahuan --
kalau lupa, `create_app()` sendiri yang tidak lengkap dan gampang
ketahuan saat baca fungsi ini.
"""

import os
import secrets

from flask import Flask
from flask_scss import Scss

from library.extensions import db


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    Scss(app)

    _configure(app)
    db.init_app(app)
    _register_blueprints(app)
    _register_context_processors(app)

    return app


def _configure(app):
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))

    # Persiapan migrasi SQLite -> PostgreSQL: cukup set env var DATABASE_URL,
    # tidak perlu ubah kode apa pun (model sudah pakai tipe kolom generik --
    # lihat library/models.py & MIGRATION.md).
    database_url = os.environ.get("DATABASE_URL", "sqlite:///database.db")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}


def _register_blueprints(app):
    from library.main.routes import main_bp
    from library.workspace.kpi_dashboard.routes import kpi_dashboard_bp
    from library.workspace.issue_monitor.routes import issue_monitor_bp
    from library.admin.user_management.routes import user_management_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(kpi_dashboard_bp)
    app.register_blueprint(issue_monitor_bp)
    app.register_blueprint(user_management_bp)


def _register_context_processors(app):
    """Suntik info role user yang lagi login ke SEMUA template, tanpa
    perlu tambahin `role=...` manual ke tiap render_template() satu-satu
    (ada belasan route yang render halaman workspace/team). Dipakai oleh
    templates/partials/top-sidebar.html buat nampilin/nyembunyiin menu
    "User Management" (khusus Super Admin) & oleh issue_monitor.html buat
    nyembunyiin tab "Issue Register" dari Member (view-only)."""

    from flask import session

    @app.context_processor
    def inject_current_role():
        role = session.get("role")
        return {
            "current_role": role,
            "is_super_admin": role == "Super Admin",
            "is_admin_or_above": role in ("Super Admin", "Admin"),
        }
