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
from library.naming import name_from_email, unique_display_name

user_management_bp = Blueprint(
    "user_management", __name__, url_prefix="/admin/users"
)


def _derived_name(email, exclude_user_id=None):
    """Display name derived from the email, made unique across users
    (optionally ignoring one user, when re-deriving on email change)."""

    def exists(candidate):
        query = User.query.filter_by(username=candidate)
        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        return query.first() is not None

    return unique_display_name(name_from_email(email), exists)


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


def _other_active_super_admins(exclude_user_id):
    """How many Super Admins, other than exclude_user_id, are both the
    Super Admin role AND currently active. An inactive Super Admin can't
    log in, so counting them as a "backup" is how the last-active-admin
    checks below used to let the only working Super Admin get demoted or
    deleted as long as some deactivated account still technically held
    the role."""
    return User.query.filter(
        User.role == "Super Admin",
        User.is_active.is_(True),
        User.id != exclude_user_id,
    ).count()


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

    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    role = data.get("role") or "Member"
    categories = data.get("categories") or []
    events = data.get("events") or []

    if not email or not password:
        return jsonify({"message": "Email and password are required."}), 400
    if len(password) < 8:
        return jsonify({"message": "Password must be at least 8 characters."}), 400
    if role not in ROLE_CHOICES:
        return jsonify({"message": "Invalid role."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "An account with this email already exists."}), 409

    # Display name is derived from the email (see library/naming.py).
    username = _derived_name(email)

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

    return jsonify({"message": f"User {username} created successfully.", "user": user.to_dict()}), 201


@user_management_bp.route("/api/users/<int:user_id>", methods=["PATCH"])
@login_required
@roles_required("Super Admin")
def api_update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    if "email" in data:
        email = (data.get("email") or "").strip()
        if email and email != user.email:
            if User.query.filter(User.email == email, User.id != user.id).first():
                return jsonify({"message": "An account with this email already exists."}), 409
            user.email = email
            # Keep the display name in sync with the new email.
            user.username = _derived_name(email, exclude_user_id=user.id)

    if "role" in data:
        role = data.get("role")
        if role not in ROLE_CHOICES:
            return jsonify({"message": "Invalid role."}), 400
        # Never let the last active Super Admin demote themselves away.
        if user.role == "Super Admin" and role != "Super Admin":
            if _other_active_super_admins(user.id) == 0:
                return jsonify({"message": "There must be at least one active Super Admin."}), 400
        user.role = role

    if "is_active" in data:
        new_active = bool(data.get("is_active"))
        if not new_active and user.role == "Super Admin":
            # A Super Admin can't deactivate their own account -- not even
            # when other active Super Admins exist. If they genuinely need
            # to step down, another Super Admin does it for them; that
            # cross-check is what the "can't delete your own account" rule
            # below already does for deletion, applied the same way here.
            if user.id == session.get("user_id"):
                return jsonify({"message": "You can't deactivate your own account. Ask another Super Admin to do it."}), 400
            # Deactivating this Super Admin must still leave at least one
            # OTHER active Super Admin able to log in and manage users --
            # otherwise there's no one left to reactivate anyone, and the
            # only fix would be editing the database directly.
            if _other_active_super_admins(user.id) == 0:
                return jsonify({"message": "There must be at least one active Super Admin."}), 400
        user.is_active = new_active
        if new_active and user.approved_at is None:
            from datetime import datetime
            user.approved_at = datetime.utcnow()

    if "password" in data and data.get("password"):
        if len(data["password"]) < 8:
            return jsonify({"message": "Password must be at least 8 characters."}), 400
        user.set_password(data["password"])

    if "categories" in data or "events" in data:
        _apply_scope(
            user,
            data.get("categories", user.categories),
            data.get("events", user.events),
        )

    db.session.commit()
    return jsonify({"message": "User updated successfully.", "user": user.to_dict()})


@user_management_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
@login_required
@roles_required("Super Admin")
def api_delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == session.get("user_id"):
        return jsonify({"message": "You can't delete your own account."}), 400

    if user.role == "Super Admin":
        if _other_active_super_admins(user.id) == 0:
            return jsonify({"message": "There must be at least one active Super Admin."}), 400

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"User {user.username} deleted successfully."})


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
