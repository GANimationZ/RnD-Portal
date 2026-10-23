from urllib.parse import urlparse

from flask import Blueprint, jsonify, render_template, request, session

from library.auth import login_required
from library.extensions import db
from library.models import ToolLink

tools_bp = Blueprint("tools", __name__, url_prefix="/workspace/tools")

KIND_CHOICES = ["Tool", "Material"]


def _is_valid_url(value):
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _serialize(item):
    data = item.to_dict()
    data["can_delete"] = (
        session.get("role") == "Super Admin" or item.created_by_id == session.get("user_id")
    )
    return data


@tools_bp.route("", methods=["GET"])
@login_required
def index():
    return render_template(
        "workspace/tools.html",
        active_nav="tools",
        username=session.get("username"),
        kind_choices=KIND_CHOICES,
    )


@tools_bp.route("/api/items", methods=["GET"])
@login_required
def api_list_items():
    items = ToolLink.query.order_by(ToolLink.name).all()
    categories = sorted({i.category for i in items})
    return jsonify({
        "items": [_serialize(i) for i in items],
        "categories": categories,
    })


@tools_bp.route("/api/items", methods=["POST"])
@login_required
def api_create_item():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    kind = (data.get("kind") or "").strip()
    category = (data.get("category") or "").strip()
    url = (data.get("url") or "").strip()
    description = (data.get("description") or "").strip()

    if not name or not category or not url:
        return jsonify({"message": "Name, category, and link are required."}), 400
    if kind not in KIND_CHOICES:
        return jsonify({"message": "Type must be Tool or Material."}), 400
    if not _is_valid_url(url):
        return jsonify({"message": "Link must be a valid http(s) URL."}), 400

    item = ToolLink(
        name=name,
        kind=kind,
        category=category,
        url=url,
        description=description or None,
        created_by_id=session.get("user_id"),
    )
    db.session.add(item)
    db.session.commit()

    return jsonify({"message": f"{kind} added successfully.", "item": _serialize(item)}), 201


@tools_bp.route("/api/items/<int:item_id>", methods=["DELETE"])
@login_required
def api_delete_item(item_id):
    item = ToolLink.query.get_or_404(item_id)

    if session.get("role") != "Super Admin" and item.created_by_id != session.get("user_id"):
        return jsonify({"message": "Only the creator or a Super Admin can delete this entry."}), 403

    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Entry deleted successfully."})
