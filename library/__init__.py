import os
import secrets

from flask import Flask
from flask_scss import Scss

from library.errors import register_error_handlers
from library.extensions import db


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    Scss(app)

    _configure(app)
    db.init_app(app)
    _register_blueprints(app)
    _register_context_processors(app)
    register_error_handlers(app)

    return app

MAX_UPLOAD_SIZE_MB = 10


def _configure(app):
    app.config["SECRET_KEY"] = _get_or_create_secret_key(app)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE_MB * 1024 * 1024

    database_url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://postgres:furryfandom649@localhost:5432/rnd_portal")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}


def _get_or_create_secret_key(app):
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key

    os.makedirs(app.instance_path, exist_ok=True)
    key_path = os.path.join(app.instance_path, "secret_key")

    if os.path.exists(key_path):
        with open(key_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    key = secrets.token_hex(32)
    with open(key_path, "w", encoding="utf-8") as f:
        f.write(key)
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass
    return key


def _register_blueprints(app):
    from library.main.routes import main_bp
    from library.workspace.kpi_dashboard.routes import kpi_dashboard_bp
    from library.workspace.issue_monitor.routes import issue_monitor_bp
    from library.workspace.tv_design.routes import tv_design_bp
    from library.admin.user_management.routes import user_management_bp
    from library.settings.routes import settings_bp
    from library.workspace.tools.routes import tools_bp
    from library.workspace.assets.routes import assets_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(kpi_dashboard_bp)
    app.register_blueprint(issue_monitor_bp)
    app.register_blueprint(tv_design_bp)
    app.register_blueprint(user_management_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(assets_bp)


def _register_context_processors(app):
    """Expose the logged-in user's role to every template."""

    from flask import session

    @app.context_processor
    def inject_current_role():
        role = session.get("role")
        return {
            "current_role": role,
            "is_super_admin": role == "Super Admin",
            "is_admin_or_above": role in ("Super Admin", "Admin"),
            "current_user_avatar": _current_user_avatar_url(),
        }


def _current_user_avatar_url():
    """Profile picture URL of the logged-in user (None if not set)."""
    from flask import session

    from library.models import User

    user_id = session.get("user_id")
    if not user_id:
        return None
    user = User.query.get(user_id)
    return user.profile_picture_url if user else None
