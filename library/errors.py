"""Halaman error kustom (403 Forbidden & 404 Not Found).

Satu tempat untuk semua penanganan error HTTP, supaya bentuk balasannya
konsisten:

- Navigasi browser biasa  -> halaman HTML (templates/errors/403.html, 404.html)
- API / fetch()           -> JSON {"message": ...} dengan status yang sama
- Request file /static/*  -> teks polos (tidak perlu render satu halaman
                             penuh hanya untuk gambar/CSS/JS yang hilang)

Untuk memicu 403 dengan pesan sendiri di route mana pun:
    abort(403, description="Pesan untuk user")
"""

from flask import Response, jsonify, render_template, request, session, url_for
from werkzeug.exceptions import Forbidden, NotFound

from library.auth import home_url, wants_json

DEFAULT_JSON_MESSAGES = {
    403: "Akses ditolak: hak akses tidak mencukupi.",
    404: "Data atau halaman yang diminta tidak ditemukan.",
}

# Deskripsi bawaan Werkzeug (bahasa Inggris) tidak ditampilkan ke user --
# hanya deskripsi kustom dari abort(..., description=...) yang dipakai.
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
