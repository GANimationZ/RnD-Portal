from functools import wraps

from flask import abort, g, redirect, request, session, url_for

from library.extensions import db
from library.models import User

ROLE_HOME_ENDPOINT = {
    "Admin": "issue_monitor.index",
}
DEFAULT_HOME_ENDPOINT = "main.kpi_dashboard"


def home_url(role=None):
    if role is None:
        role = session.get("role")
    return url_for(ROLE_HOME_ENDPOINT.get(role, DEFAULT_HOME_ENDPOINT))


def wants_json():
    if request.is_json:
        return True
    path = request.path.rstrip("/")
    if "/api/" in request.path or path.endswith("/api"):
        return True
    accepts = request.accept_mimetypes
    best = accepts.best_match(["application/json", "text/html"])
    return best == "application/json" and accepts[best] > accepts["text/html"]


def _load_live_session_user():
    if "_live_session_user" in g:
        return g._live_session_user

    user = db.session.get(User, session["user_id"])

    if user is None or not user.is_active:
        session.clear()
        g._live_session_user = None
        return None

    session["role"] = user.role
    g._live_session_user = user
    return user


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.onboard"))

        if _load_live_session_user() is None:
            return redirect(url_for("main.onboard"))

        return f(*args, **kwargs)

    return decorated_function


def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("main.onboard"))

            if _load_live_session_user() is None:
                return redirect(url_for("main.onboard"))

            if session.get("role") not in roles:
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator
