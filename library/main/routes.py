"""
Blueprint `main` -- route umum yang tidak spesifik ke satu workspace:
autentikasi (onboard/register/login/logout), render halaman workspace
yang belum punya blueprint sendiri (KPI Dashboard, TV Design, Tools),
dan halaman Team.

Tidak dikasih url_prefix supaya path URL-nya persis sama seperti
sebelumnya (mis. tetap "/", "/login", "/workspace/tools", dst) -- yang
berubah cuma endpoint name-nya jadi diawali "main." (lihat url_for di
library/auth.py & di dalam file ini).
"""

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from library.auth import login_required, roles_required
from library.extensions import db
from library.models import User

main_bp = Blueprint("main", __name__)


# ==================== Autentikasi ====================

@main_bp.route("/", methods=["GET"])
def onboard():
    if "user_id" in session:
        return redirect(url_for("main.kpi_dashboard"))
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

        new_user = User(username=username, email=email, role="Member")
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": f"User {username} successfully created."}), 201

    return render_template("auth/auth.html")


@main_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request."}), 400

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Please fill the empty box."}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password."}), 401
    if not user.is_active:
        return jsonify({"error": "Akun ini sudah dinonaktifkan. Hubungi Super Admin."}), 403

    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role

    return jsonify({"message": f"Welcome back, {username}!"}), 200


@main_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out."}), 200


# ==================== Halaman Workspace ====================

@main_bp.route("/workspace/kpi-dashboard", methods=["GET"])
@login_required
@roles_required("Super Admin", "Member")  # poin 1: QA (Admin) tidak boleh lihat KPI Dashboard
def kpi_dashboard():
    return render_template(
        "workspace/kpi_dashboard.html",
        active_nav="kpi-dashboard",
        username=session.get("username"),
    )


@main_bp.route("/workspace/tv-design-concept", methods=["GET"])
@login_required
def tv_design_concept():
    return render_template(
        "workspace/tv_design_concept.html",
        active_nav="analyse",
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


# ==================== Halaman Team ====================

@main_bp.route("/team/structure", methods=["GET"])
@login_required
def org_structure():
    return render_template(
        "team/organization.html",
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
