"""
Flask blueprint User Management.

- Halaman `/admin/users` (list user + form tambah/edit) -- khusus role
  "Super Admin" (lihat library/auth.py:roles_required).
- API CRUD user, termasuk assign role & scope (category/event) per user.
  Scope disimpan ternormalisasi lewat UserCategoryScope/UserEventScope
  (satu user boleh punya banyak category & banyak event).
- API `/api/assignable` dipakai form "Issue Register" (issue_monitor) buat
  ngisi combobox "Ditugaskan ke" -- balikin Member yang scope-nya
  mencakup category & event issue yang lagi dibuat. Endpoint ini boleh
  diakses Admin (QA) juga, bukan cuma Super Admin, karena Admin-lah yang
  bikin issue & butuh milih assignee-nya.
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
    """Ganti total scope category & event milik `user` sesuai list baru
    (dipakai bareng buat create & update supaya konsisten)."""
    UserCategoryScope.query.filter_by(user_id=user.id).delete()
    UserEventScope.query.filter_by(user_id=user.id).delete()

    for category in dict.fromkeys(categories):  # dedupe, jaga urutan
        if category in CATEGORY_CHOICES:
            db.session.add(UserCategoryScope(user_id=user.id, category=category))

    for event in dict.fromkeys(events):
        if event in EVENT_CHOICES:
            db.session.add(UserEventScope(user_id=user.id, event=event))


# ==================== Halaman ====================

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
    db.session.add(user)
    db.session.flush()  # supaya user.id kebentuk buat _apply_scope

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
        # Jangan sampai Super Admin terakhir kehapus role-nya sendiri
        # sampai tidak ada Super Admin tersisa sama sekali.
        if user.role == "Super Admin" and role != "Super Admin":
            remaining = User.query.filter(User.role == "Super Admin", User.id != user.id).count()
            if remaining == 0:
                return jsonify({"message": "Minimal harus ada satu Super Admin."}), 400
        user.role = role

    if "is_active" in data:
        user.is_active = bool(data.get("is_active"))

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


# ==================== API: Assignee combobox (Issue Register) ====================

@user_management_bp.route("/api/assignable", methods=["GET"])
@login_required
@roles_required("Super Admin", "Admin")
def api_assignable_users():
    """Dipanggil issue-monitor.js tiap category & event di form Register
    sudah sama-sama terisi. Balikin Member (role="Member", aktif) yang
    scope-nya mencakup KEDUA nilai tsb."""
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
