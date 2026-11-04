import re
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request, session
from sqlalchemy.exc import IntegrityError

from library.auth import login_required, roles_required
from library.extensions import db
from library.models import PvAsset, PvAssetScan

assets_bp = Blueprint("assets", __name__, url_prefix="/workspace/assets")

# Same access rule as the KPI Dashboard: QA (Admin) has no access -> 403 page.
ALLOWED_ROLES = ("Super Admin", "Member")

NAME_MAX = 120
SERIAL_MAX = 60
HISTORY_LIMIT = 6


def serial_key(value):
    """Normalized serial: no whitespace/control chars, upper case."""
    return re.sub(r"[\s\x00-\x1f\x7f]+", "", value or "").upper()


def name_key(value):
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _history():
    rows = PvAssetScan.query.order_by(PvAssetScan.id.desc()).limit(HISTORY_LIMIT).all()
    return [r.to_dict() for r in rows]


def _unknown_count():
    return PvAssetScan.query.filter_by(result="unknown").count()


# ==================== Page ====================

@assets_bp.route("", methods=["GET"])
@login_required
@roles_required(*ALLOWED_ROLES)
def index():
    return render_template(
        "workspace/assets.html",
        active_nav="assets",
        username=session.get("username"),
    )


# ==================== API ====================

@assets_bp.route("/api/assets", methods=["GET"])
@login_required
@roles_required(*ALLOWED_ROLES)
def api_list_assets():
    assets = PvAsset.query.order_by(PvAsset.id).all()
    return jsonify({
        "assets": [a.to_dict() for a in assets],
        "unknown_count": _unknown_count(),
        "history": _history(),
    })


def _parse_asset_payload(data):
    """Validate name + serial. Returns (name, serial, error_response_or_None)."""
    name = re.sub(r"\s+", " ", (data.get("name") or "")).strip()
    serial = (data.get("serial") or "").strip()

    if not name and not serial:
        return None, None, (jsonify({"message": "Item Name and Serial Number are required.", "fields": ["name", "serial"]}), 400)
    if not name:
        return None, None, (jsonify({"message": "Item Name is required.", "fields": ["name"]}), 400)
    if not serial:
        return None, None, (jsonify({"message": "Serial Number is required.", "fields": ["serial"]}), 400)
    if len(name) > NAME_MAX:
        return None, None, (jsonify({"message": f"Item Name must be at most {NAME_MAX} characters.", "fields": ["name"]}), 400)
    if len(serial) > SERIAL_MAX:
        return None, None, (jsonify({"message": f"Serial Number must be at most {SERIAL_MAX} characters.", "fields": ["serial"]}), 400)
    return name, serial, None


def _duplicate_response(duplicate):
    return jsonify({
        "message": f'This Serial Number is already registered for "{duplicate.name}".',
        "fields": ["serial"],
    }), 409


@assets_bp.route("/api/assets", methods=["POST"])
@login_required
@roles_required(*ALLOWED_ROLES)
def api_create_asset():
    name, serial, error = _parse_asset_payload(request.get_json(silent=True) or {})
    if error:
        return error

    key = serial_key(serial)
    duplicate = PvAsset.query.filter_by(serial_key=key).first()
    if duplicate:
        return _duplicate_response(duplicate)

    asset = PvAsset(
        name=name,
        serial_number=serial,
        serial_key=key,
        created_by_id=session.get("user_id"),
    )
    db.session.add(asset)
    try:
        db.session.commit()
    except IntegrityError:  # two people adding the same serial at once
        db.session.rollback()
        return jsonify({"message": "This Serial Number is already registered.", "fields": ["serial"]}), 409

    return jsonify({"message": "Asset added successfully.", "asset": asset.to_dict()}), 201


@assets_bp.route("/api/assets/<int:asset_id>", methods=["PUT"])
@login_required
@roles_required(*ALLOWED_ROLES)
def api_update_asset(asset_id):
    asset = db.session.get(PvAsset, asset_id)
    if asset is None:
        return jsonify({"message": "Asset not found."}), 404

    name, serial, error = _parse_asset_payload(request.get_json(silent=True) or {})
    if error:
        return error

    key = serial_key(serial)
    duplicate = PvAsset.query.filter(PvAsset.serial_key == key, PvAsset.id != asset.id).first()
    if duplicate:
        return _duplicate_response(duplicate)

    # A previous scan verified the OLD name/serial, so any change to either
    # sends the asset back to "Not Checked" and it has to be scanned again.
    changed = name != asset.name or key != asset.serial_key
    asset.name = name
    asset.serial_number = serial
    asset.serial_key = key
    if changed:
        asset.scan_status = "pending"
        asset.scanned_at = None
        asset.scanned_by_id = None

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "This Serial Number is already registered.", "fields": ["serial"]}), 409

    return jsonify({
        "message": "Asset updated successfully." if not changed else "Asset updated. Scan it again to re-verify.",
        "asset": asset.to_dict(),
        "reset_scan": changed,
    })


@assets_bp.route("/api/assets/<int:asset_id>", methods=["DELETE"])
@login_required
@roles_required(*ALLOWED_ROLES)
def api_delete_asset(asset_id):
    asset = db.session.get(PvAsset, asset_id)
    if asset is None:
        return jsonify({"message": "Asset not found."}), 404

    # Keep the scan history (it stores the scanned serial itself), just
    # detach it from the asset that no longer exists.
    PvAssetScan.query.filter_by(asset_id=asset.id).update({"asset_id": None})
    name = asset.name
    db.session.delete(asset)
    db.session.commit()

    return jsonify({"message": f'Asset "{name}" deleted.'})


@assets_bp.route("/api/assets/scan", methods=["POST"])
@login_required
@roles_required(*ALLOWED_ROLES)
def api_scan_asset():
    data = request.get_json(silent=True) or {}
    raw_serial = (data.get("serial") or "").strip()
    input_name = re.sub(r"\s+", " ", (data.get("name") or "")).strip()

    key = serial_key(raw_serial)
    if not key:
        return jsonify({"message": "Serial Number is required."}), 400
    if len(raw_serial) > 120 or len(input_name) > 120:
        return jsonify({"message": "Scanned value is too long."}), 400

    now = datetime.utcnow()
    user_id = session.get("user_id")
    asset = PvAsset.query.filter_by(serial_key=key).first()

    already_scanned = False
    if asset is None:
        result = "unknown"
    else:
        already_scanned = asset.scan_status != "pending"
        result = "mismatch" if input_name and name_key(input_name) != name_key(asset.name) else "match"
        asset.scan_status = result
        asset.scanned_at = now
        asset.scanned_by_id = user_id

    db.session.add(PvAssetScan(
        asset_id=asset.id if asset else None,
        scanned_serial=raw_serial,
        input_name=input_name or None,
        result=result,
        scanned_by_id=user_id,
        scanned_at=now,
    ))
    db.session.commit()

    return jsonify({
        "result": result,
        "already_scanned": already_scanned,
        "asset": asset.to_dict() if asset else None,
        "input_name": input_name,
        "unknown_count": _unknown_count(),
        "history": _history(),
    })
