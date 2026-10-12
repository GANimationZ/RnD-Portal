"""Custom error pages (403 Forbidden & 404 Not Found).

One place for all HTTP error handling, so responses stay consistent:

- Normal browser navigation -> HTML page (templates/errors/403.html, 404.html)
- API / fetch()             -> JSON {"message": ...} with the same status
- /static/* file requests   -> plain text (no need to render a full page
                               for a missing image/CSS/JS)

To trigger a 403 with a custom message from any route:
    abort(403, description="Message for the user")
"""

from flask import Response, jsonify, render_template, request, session, url_for
from werkzeug.exceptions import Forbidden, NotFound

from library.auth import home_url, wants_json

DEFAULT_JSON_MESSAGES = {
    403: "Access denied: insufficient permissions.",
    404: "The requested data or page was not found.",
}

# Werkzeug's built-in descriptions are not shown to the user -- only custom
# descriptions passed via abort(..., description=...) are used.
_WERKZEUG_DEFAULTS = {403: Forbidden.description, 404: NotFound.description}


def _custom_description(status, error):
    description = getattr(error, "description", None)
    if description and description != _WERKZEUG_DEFAULTS[status]:
        return description
    return None


def _respond(status, error):
    detail = _custom_description(status, error)

    if request.path.startswith("/static/"):
        return Response("Not Found" if status == 404 else "Forbidden", status=status, mimetype="text/plain")

    if wants_json():
        return jsonify({"message": detail or DEFAULT_JSON_MESSAGES[status]}), status

    logged_in = "user_id" in session
    return (
        render_template(
            f"errors/{status}.html",
            detail=detail,
            logged_in=logged_in,
            home_url=home_url() if logged_in else url_for("main.onboard"),
        ),
        status,
    )


def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(error):
        return _respond(403, error)

    @app.errorhandler(404)
    def not_found(error):
        return _respond(404, error)
