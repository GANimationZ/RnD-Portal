"""Auth decorators & helpers shared across all blueprints."""

from functools import wraps

from flask import abort, redirect, request, session, url_for

# Landing page after login (and the "Back to Home" button on error pages)
# per role. Roles not listed here use DEFAULT_HOME_ENDPOINT.
#
# QA (role "Admin") has no access to the KPI Dashboard, so their landing
# page is Issue Monitoring -- otherwise every login/redirect would dead-end
# on a page that role is denied.
ROLE_HOME_ENDPOINT = {
    "Admin": "issue_monitor.index",
}
DEFAULT_HOME_ENDPOINT = "main.kpi_dashboard"


def home_url(role=None):
    """Home page URL for `role` (defaults to the logged-in user's role)."""
    if role is None:
        role = session.get("role")
    return url_for(ROLE_HOME_ENDPOINT.get(role, DEFAULT_HOME_ENDPOINT))


def wants_json():
    """True if this request comes from fetch()/an API and should get a
    JSON reply instead of an HTML page. Shared by the decorators below and
    the error handlers (library/errors.py) so behavior stays consistent."""
    if request.is_json:
        return True
    path = request.path.rstrip("/")
    if "/api/" in request.path or path.endswith("/api"):
        return True
    # Clients that explicitly prefer JSON over HTML via the Accept header.
    # Accept "*/*" (fetch() default) is intentionally not counted.
    accepts = request.accept_mimetypes
    best = accepts.best_match(["application/json", "text/html"])
    return best == "application/json" and accepts[best] > accepts["text/html"]


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.onboard"))
        return f(*args, **kwargs)

    return decorated_function


def roles_required(*roles):
    """Use after @login_required. If the role doesn't match, triggers an
    HTTP 403 via abort(). The 403 error handler (library/errors.py) decides
    the response shape: an "Access Denied" page for normal navigation, or
    JSON for API/fetch calls so the frontend can show a proper error.

    Deliberately does NOT redirect to the dashboard: for a role that is
    denied from the dashboard itself (e.g. Admin vs KPI Dashboard) that
    redirect would end in a redirect loop."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("main.onboard"))

            if session.get("role") not in roles:
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator
