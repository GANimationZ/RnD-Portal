import os

from flask import Blueprint, jsonify, render_template, request, session

from library.auth import login_required
from library.extensions import db
from library.files import IMAGE_EXTENSIONS, get_extension, get_upload_dir, save_upload
from library.models import User
from library.naming import name_from_email, unique_display_name

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

MAX_PROFILE_PICTURE_BYTES = 2 * 1024 * 1024
PROFILE_UPLOAD_SUBDIR = "profiles"


def _current_user():
    return User.query.get(session["user_id"])


@settings_bp.route("", methods=["GET"])
@login_required
def index():
    user = _current_user()
    return render_template(
        "settings.html",
        active_nav="settings",
        username=session.get("username"),
        user=user,
    )


@settings_bp.route("/profile", methods=["POST"])
@login_required
def update_profile():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request."}), 400

    email = (data.get("email") or "").strip()
    job_title = (data.get("job_title") or "").strip()

    if not email:
        return jsonify({"error": "Email can't be empty."}), 400

    user = _current_user()

    if email != user.email:
        if User.query.filter(User.email == email, User.id != user.id).first():
            return jsonify({"error": "An account with this email already exists."}), 409
        user.email = email
        user.username = unique_display_name(
            name_from_email(email),
            lambda candidate: User.query.filter(
                User.username == candidate, User.id != user.id
            ).first() is not None,
        )
        session["username"] = user.username

    user.job_title = job_title or None
    db.session.commit()

    return jsonify({"message": "Profile updated successfully.", "username": user.username}), 200


@settings_bp.route("/password", methods=["POST"])
@login_required
def update_password():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request."}), 400

    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or ""

    user = _current_user()

    if not user.check_password(current_password):
        return jsonify({"error": "Current password is incorrect."}), 400
    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters."}), 400
    if new_password != confirm_password:
        return jsonify({"error": "Password confirmation doesn't match."}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({"message": "Password changed successfully. Please log in again if prompted."}), 200


def _remove_picture_file(filename):
    if not filename:
        return
    path = os.path.join(get_upload_dir(PROFILE_UPLOAD_SUBDIR), filename)
    if os.path.exists(path):
        os.remove(path)


@settings_bp.route("/profile-picture", methods=["POST"])
@login_required
def upload_profile_picture():
    file = request.files.get("picture")
    if not file or not file.filename:
        return jsonify({"error": "Please choose an image first."}), 400

    if get_extension(file.filename) not in IMAGE_EXTENSIONS:
        return jsonify({"error": "Unsupported format. Use PNG, JPG, GIF, or WEBP."}), 400

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_PROFILE_PICTURE_BYTES:
        return jsonify({"error": "Image is too large. Maximum size is 2 MB."}), 400

    user = _current_user()
    old_filename = user.profile_picture
    user.profile_picture = save_upload(file, PROFILE_UPLOAD_SUBDIR, f"user{user.id}")
    db.session.commit()
    _remove_picture_file(old_filename)

    return jsonify({
        "message": "Profile picture updated.",
        "picture_url": user.profile_picture_url,
    }), 200


@settings_bp.route("/profile-picture", methods=["DELETE"])
@login_required
def delete_profile_picture():
    user = _current_user()
    old_filename = user.profile_picture
    user.profile_picture = None
    db.session.commit()
    _remove_picture_file(old_filename)

    return jsonify({"message": "Profile picture removed."}), 200
