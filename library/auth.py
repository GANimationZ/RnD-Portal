"""Auth decorators shared across all blueprints."""

from functools import wraps

from flask import jsonify, redirect, request, session, url_for


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.onboard"))
        return f(*args, **kwargs)

    return decorated_function


def roles_required(*roles):
    """Use after @login_required. Redirects HTML page requests back to the
    dashboard, but returns 403 JSON for API/fetch requests so the frontend
    can show a proper error instead of an unexpected HTML response."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("main.onboard"))

            if session.get("role") not in roles:
                wants_json = (
                    request.is_json
                    or request.path.startswith("/admin/users/api")
                    or request.path.rstrip("/").endswith("/api")
                    or "/api/" in request.path
                )
                if wants_json:
                    return jsonify({"message": "Akses ditolak: hak akses tidak mencukupi."}), 403
                return redirect(url_for("main.kpi_dashboard"))

            return f(*args, **kwargs)

        return decorated_function

    return decorator
