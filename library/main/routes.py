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
from library.naming import name_from_email, unique_display_name

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

        email = (data.get("email") or "").strip()
        password = data.get("password")
        retype = data.get("retype")

        if not email or not password:
            return jsonify({"error": "Please fill all the empty boxes."}), 400
        if len(password) < 8:
            return jsonify({"error": "Minimal 8 Characters long."}), 400
        if password != retype:
            return jsonify({"error": "Password does not match"}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "An account with this email already exists."}), 409

        # No username field anymore -- the display name is derived from
        # the email's local-part (see library/naming.py), e.g.
        # "john.doe@test.com" -> "John Doe". Suffixed with " (2)", " (3)"
        # etc on the rare case two different emails produce the same name.
        display_name = unique_display_name(
            name_from_email(email),
            lambda candidate: User.query.filter_by(username=candidate).first() is not None,
        )

        new_user = User(username=display_name, email=email, role="Member", is_active=False)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": f"Account {display_name} created. Waiting for Super Admin approval before you can log in."}), 201

    return render_template("auth/auth.html")


def _login_error(message, status, field=None):
    """Uniform login error response. `field` ("email"/"password") tells
    the frontend which input to highlight and focus."""
    payload = {"error": message}
    if field:
        payload["field"] = field
    return jsonify(payload), status


@main_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _login_error("Invalid login request. Reload the page and try again.", 400)

    email = data.get("email")
    password = data.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return _login_error("Invalid login request. Reload the page and try again.", 400)

    email = email.strip()
    if not email:
        return _login_error("Email is required.", 400, "email")
    if not password:
        return _login_error("Password is required.", 400, "password")

    try:
        user = User.query.filter_by(email=email).first()
    except SQLAlchemyError:
        current_app.logger.exception("Login failed: database error")
        return _login_error("A server error occurred. Please try again shortly.", 500)

    # Distinct messages (email not found vs wrong password) so the person
    # knows exactly what to fix. Account status (pending/inactive) is only
    # revealed AFTER the password checks out, so someone without the
    # password can't probe an account's status.
    if user is None:
        return _login_error("Email not found.", 401, "email")
    if not user.check_password(password):
        return _login_error("Incorrect password. Please try again.", 401, "password")
    if not user.is_active:
        message = (
            "Your account is waiting for Super Admin approval before you can log in."
            if user.approved_at is None
            else "This account has been deactivated. Contact your Super Admin."
        )
        return _login_error(message, 403)

    session.clear()
    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role

    return jsonify({
        "message": f"Login successful. Welcome, {user.username}!",
        # Post-login destination is decided server-side (per role) so the
        # frontend doesn't need to know access rules -- see
        # library/auth.py:home_url().
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
