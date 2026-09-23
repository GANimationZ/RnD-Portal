"""User Management blueprint.

- `/admin/users` page (user list + create/edit form) -- Super Admin only.
- CRUD API for users, including role and scope (category/event) per user.
  Scope is normalized via UserCategoryScope/UserEventScope (a user can
  have several categories and events).
- `/api/assignable` is used by the Issue Register form to fill the
  "Assignee" combobox -- returns Members whose scope covers the given
  category and event. Also reachable by Admin (QA), since QA is who
  creates issues and picks the assignee.
"""

from flask import Blueprint, jsonify, render_template, request, session

from library.auth import login_required, roles_required
from library.extensions import db
from library.models import (
    CATEGORY_CHOICES,
    EVENT_CHOICES,
    ROLE_CHOICES,
    User,
    UserCategoryScope,
    UserEventScope,
)

user_management_bp = Blueprint(
    "user_management", __name__, url_prefix="/admin/users"
)


def _apply_scope(user, categories, events):
    """Replace a user's full category/event scope with the given lists
    (shared by create and update for consistency)."""
    UserCategoryScope.query.filter_by(user_id=user.id).delete()
    UserEventScope.query.filter_by(user_id=user.id).delete()

    for category in dict.fromkeys(categories):  # dedupe, keep order
        if category in CATEGORY_CHOICES:
            db.session.add(UserCategoryScope(user_id=user.id, category=category))

    for event in dict.fromkeys(events):
        if event in EVENT_CHOICES:
            db.session.add(UserEventScope(user_id=user.id, event=event))


# ==================== Page ====================

@user_management_bp.route("", methods=["GET"])
@login_required
@roles_required("Super Admin")
def index():
    all_users = User.query.order_by(User.username).all()
    return render_template(
        "admin/user_management.html",
        active_nav="user-management",
        username=session.get("username"),
        users=all_users,
        role_choices=ROLE_CHOICES,
        category_choices=CATEGORY_CHOICES,
        event_choices=EVENT_CHOICES,
    )


# ==================== API: CRUD User ====================

@user_management_bp.route("/api/users", methods=["GET"])
@login_required
@roles_required("Super Admin")
def api_list_users():
    all_users = User.query.order_by(User.username).all()
    return jsonify({"users": [u.to_dict() for u in all_users]})


@user_management_bp.route("/api/users", methods=["POST"])
@login_required
@roles_required("Super Admin")
def api_create_user():
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    role = data.get("role") or "Member"
    categories = data.get("categories") or []
    events = data.get("events") or []

    if not username or not email or not password:
        return jsonify({"message": "Username, email, dan password wajib diisi."}), 400
    if len(password) < 8:
        return jsonify({"message": "Password minimal 8 karakter."}), 400
    if role not in ROLE_CHOICES:
        return jsonify({"message": "Role tidak valid."}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username sudah dipakai."}), 409

    user = User(username=username, email=email, role=role)
    user.set_password(password)
    # Created directly by Super Admin -> treated as already verified
    # (approved_at set), so if later deactivated the status_label becomes
    # "Inactive" rather than "Pending" again.
    from datetime import datetime
    user.approved_at = datetime.utcnow()
    db.session.add(user)
    db.session.flush()  # populate user.id for _apply_scope

    _apply_scope(user, categories, events)
    db.session.commit()

    return jsonify({"message": f"User {username} berhasil dibuat.", "user": user.to_dict()}), 201


@user_management_bp.route("/api/users/<int:user_id>", methods=["PATCH"])
@login_required
@roles_required("Super Admin")
def api_update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    if "email" in data:
        email = (data.get("email") or "").strip()
        if email:
            user.email = email

    if "role" in data:
        role = data.get("role")
        if role not in ROLE_CHOICES:
            return jsonify({"message": "Role tidak valid."}), 400
        # Never let the last Super Admin demote themselves away.
        if user.role == "Super Admin" and role != "Super Admin":
            remaining = User.query.filter(User.role == "Super Admin", User.id != user.id).count()
            if remaining == 0:
                return jsonify({"message": "Minimal harus ada satu Super Admin."}), 400
        user.role = role

    if "is_active" in data:
        new_active = bool(data.get("is_active"))
        user.is_active = new_active
        if new_active and user.approved_at is None:
            from datetime import datetime
            user.approved_at = datetime.utcnow()

    if "password" in data and data.get("password"):
        if len(data["password"]) < 8:
            return jsonify({"message": "Password minimal 8 karakter."}), 400
        user.set_password(data["password"])

    if "categories" in data or "events" in data:
        _apply_scope(
            user,
            data.get("categories", user.categories),
            data.get("events", user.events),
        )

    db.session.commit()
    return jsonify({"message": "User berhasil diperbarui.", "user": user.to_dict()})


@user_management_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
@login_required
@roles_required("Super Admin")
def api_delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == session.get("user_id"):
        return jsonify({"message": "Tidak bisa menghapus akun sendiri."}), 400

    if user.role == "Super Admin":
        remaining = User.query.filter(User.role == "Super Admin", User.id != user.id).count()
        if remaining == 0:
            return jsonify({"message": "Minimal harus ada satu Super Admin."}), 400

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"User {user.username} berhasil dihapus."})


# ==================== API: assignee combobox (Issue Register) ====================

@user_management_bp.route("/api/assignable", methods=["GET"])
@login_required
@roles_required("Super Admin", "Admin")
def api_assignable_users():
    """Called by issue-monitor.js once both category and event are
    selected in the Register form. Returns active Members whose scope
    covers both values."""
    category = (request.args.get("category") or "").strip()
    event = (request.args.get("event") or "").strip()

    if not category or not event:
        return jsonify({"users": []})

    candidates = (
        User.query.filter_by(role="Member", is_active=True)
        .join(UserCategoryScope)
        .filter(UserCategoryScope.category == category)
        .join(UserEventScope, UserEventScope.user_id == User.id)
        .filter(UserEventScope.event == event)
        .order_by(User.username)
        .all()
    )

    return jsonify({
        "users": [{"id": u.id, "username": u.username} for u in candidates]
    })
