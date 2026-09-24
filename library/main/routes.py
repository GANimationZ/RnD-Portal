"""Blueprint `main`: general routes not tied to one workspace --
auth (onboard/register/login/logout), pages without their own blueprint
yet (KPI Dashboard, Tools), and Team pages.

No url_prefix, so URL paths stay the same as before ("/", "/login",
"/workspace/tools", etc) -- only the endpoint name gains a "main."
prefix (see url_for usage in library/auth.py and this file).
"""

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session
from sqlalchemy.exc import SQLAlchemyError

from library.auth import home_url, login_required, roles_required
from library.extensions import db
from library.models import User

main_bp = Blueprint("main", __name__)


# ==================== Auth ====================

@main_bp.route("/", methods=["GET"])
def onboard():
    if "user_id" in session:
        return redirect(home_url())
    return render_template("auth/auth.html")


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request."}), 400

        username = data.get("username")
        password = data.get("password")
        email = data.get("email")
        retype = data.get("retype")

        if not username or not password or not email:
            return jsonify({"error": "Please fill all the empty boxes."}), 400
        if len(password) < 8:
            return jsonify({"error": "Minimal 8 Characters long."}), 400
        if password != retype:
            return jsonify({"error": "Password does not match"}), 400
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Already taken."}), 409

        new_user = User(username=username, email=email, role="Member", is_active=False)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": f"Akun {username} berhasil dibuat. Menunggu persetujuan Super Admin sebelum bisa login."}), 201

    return render_template("auth/auth.html")


def _login_error(message, status, field=None):
    """Balasan error login yang seragam. `field` ("username"/"password")
    memberi tahu frontend kolom mana yang perlu di-highlight & difokuskan."""
    payload = {"error": message}
    if field:
        payload["field"] = field
    return jsonify(payload), status


@main_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _login_error("Permintaan login tidak valid. Muat ulang halaman lalu coba lagi.", 400)

    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return _login_error("Permintaan login tidak valid. Muat ulang halaman lalu coba lagi.", 400)

    username = username.strip()
    if not username:
        return _login_error("Username wajib diisi.", 400, "username")
    if not password:
        return _login_error("Password wajib diisi.", 400, "password")

    try:
        user = User.query.filter_by(username=username).first()
    except SQLAlchemyError:
        current_app.logger.exception("Login gagal: error database")
        return _login_error("Terjadi kesalahan pada server. Silakan coba lagi beberapa saat lagi.", 500)

    # Pesan dibedakan (username tidak ada vs password salah) supaya user tahu
    # persis apa yang harus dikoreksi. Status akun (menunggu persetujuan /
    # nonaktif) baru diberitahukan SETELAH password benar, jadi orang yang
    # tidak punya password tidak bisa mengintip status akun.
    if user is None:
        return _login_error("Username tidak ditemukan.", 401, "username")
    if not user.check_password(password):
        return _login_error("Password salah. Silakan coba lagi.", 401, "password")
    if not user.is_active:
        message = (
            "Akun Anda menunggu persetujuan Super Admin sebelum bisa login."
            if user.approved_at is None
            else "Akun ini sudah dinonaktifkan. Hubungi Super Admin."
        )
        return _login_error(message, 403)

    session.clear()
    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role

    return jsonify({
        "message": f"Login berhasil. Selamat datang, {user.username}!",
        # Tujuan setelah login ditentukan backend (per role) supaya frontend
        # tidak perlu tahu aturan akses -- lihat library/auth.py:home_url().
        "redirect": home_url(user.role),
    }), 200


@main_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out."}), 200


# ==================== Workspace pages ====================

@main_bp.route("/workspace/kpi-dashboard", methods=["GET"])
@login_required
@roles_required("Super Admin", "Member")  # QA (Admin) has no access -> 403 page
def kpi_dashboard():
    return render_template(
        "workspace/kpi_dashboard.html",
        active_nav="kpi-dashboard",
        username=session.get("username"),
    )


@main_bp.route("/workspace/tools", methods=["GET"])
@login_required
def tools():
    return render_template(
        "workspace/tools.html",
        active_nav="tools",
        username=session.get("username"),
    )


# ==================== Team pages ====================

@main_bp.route("/team/structure", methods=["GET"])
@login_required
def org_structure():
    return render_template(
        "team/structure.html",
        active_nav="structure",
        username=session.get("username"),
    )


@main_bp.route("/team/others", methods=["GET"])
@login_required
def team_others():
    return render_template(
        "team/others.html",
        active_nav="others",
        username=session.get("username"),
    )
