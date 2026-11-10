from flask import Response, jsonify, render_template, request, session, url_for
from werkzeug.exceptions import Forbidden, NotFound, RequestEntityTooLarge

from library.auth import home_url, wants_json

DEFAULT_JSON_MESSAGES = {
    403: "Access denied: insufficient permissions.",
    404: "The requested data or page was not found.",
    413: "Maximum file size upload up to 10 MB.",
}

_WERKZEUG_DEFAULTS = {
    403: Forbidden.description,
    404: NotFound.description,
    413: RequestEntityTooLarge.description,
}


def _custom_description(status, error):
    description = getattr(error, "description", None)
    if description and description != _WERKZEUG_DEFAULTS[status]:
        return description
    return None


def _respond(status, error):
    detail = _custom_description(status, error)

    if request.path.startswith("/static/"):
        plain = {404: "Not Found", 403: "Forbidden"}.get(status, "Error")
        return Response(plain, status=status, mimetype="text/plain")

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

    @app.errorhandler(413)
    def too_large(error):
        return _respond(413, error)
