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
    """Re-check the session against the DB on every request, so a
    deactivated/demoted/deleted account is caught immediately instead of
    staying valid until the session naturally expires. Cached on flask.g
    since @login_required + @roles_required can both run in one request.
    Keeps session["role"] in sync, or clears the session and returns None
    if the account is gone/inactive."""
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
    """Use after @login_required. abort(403) is handled centrally by
    library/errors.py, which already returns JSON for API/fetch requests
    and the 403 page for plain browser navigation -- no need to
    special-case that here too."""

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
