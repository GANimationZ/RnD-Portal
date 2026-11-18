import json
import re
from datetime import datetime
from io import BytesIO

from flask import Blueprint, jsonify, render_template, request, send_file, session
from sqlalchemy.exc import IntegrityError

from library.auth import login_required, roles_required
from library.extensions import db
from library.models import PvAsset, PvAssetScan

from .importer import (
    DEFAULT_OWNER,
    MAX_FILE_BYTES,
    OWNER_MAX,
    SERIAL_RULE,
    ImportFormatError,
    analyze_rows,
    build_template_workbook,
    collapse_spaces,
    name_key,
    is_valid_serial,
    normalize_serial,
    parse_assets_workbook,
)

assets_bp = Blueprint("assets", __name__, url_prefix="/workspace/assets")

# Same access rule as the KPI Dashboard: QA (Admin) has no access -> 403 page.
ALLOWED_ROLES = ("Super Admin", "Member")

NAME_MAX = 120
LOCATION_MAX = 120
HISTORY_LIMIT = 3  # "Recent scans" shows only the last 3


def serial_key(value):
    """Normalized serial: no whitespace/control chars, upper case."""
    return re.sub(r"[\s\x00-\x1f\x7f]+", "", value or "").upper()


def _history():
    # "invalid" is never recorded now; the filter hides any left from before.
    rows = (PvAssetScan.query.filter(PvAssetScan.result != "invalid")
            .order_by(PvAssetScan.id.desc()).limit(HISTORY_LIMIT).all())
    return [r.to_dict() for r in rows]


def owner_resolver():
    """Returns f(raw) -> the owner exactly as already stored (matched without
    regard to case, so "sqa" and "SQA" are one owner), or the cleaned raw text
    for a brand-new owner. New owners are remembered, so one import / request
    keeps a single spelling."""
    known = {DEFAULT_OWNER.lower(): DEFAULT_OWNER}  # "pv" is always "PV"
    for (value,) in db.session.query(PvAsset.owner).distinct():
        if value:
            known.setdefault(value.lower(), value)

    def resolve(raw):
        cleaned = re.sub(r"\s+", " ", raw or "").strip()
        if not cleaned:
            return ""
        return known.setdefault(cleaned.lower(), cleaned)

    return resolve


def owner_resolver_empty():
    known = {DEFAULT_OWNER.lower(): DEFAULT_OWNER}

    def resolve(raw):
        cleaned = re.sub(r"\s+", " ", raw or "").strip()
        return known.setdefault(cleaned.lower(), cleaned) if cleaned else ""

    return resolve


def purge_scans(asset_ids=(), serial_keys=()):
    """Delete scan records that are no longer true after an asset changed:
    the scans of those assets, and scans (of no asset) of those serial numbers.
    This is what makes "Not PV" / Recent scans follow an edit the same way a
    Replace import resets everything."""
    asset_ids = {i for i in asset_ids if i}
    serial_keys = {k for k in serial_keys if k}
    if not asset_ids and not serial_keys:
        return 0
    removed = 0
    for scan in PvAssetScan.query.all():
        if (scan.asset_id in asset_ids) or (
            scan.asset_id is None and serial_key(scan.scanned_serial) in serial_keys
        ):
            db.session.delete(scan)
            removed += 1
    return removed


def _scan_state():
    return {"unknown_count": _unknown_count(), "history": _history()}


def _unknown_count():
    # Scans of a valid-format serial that is not a registered PV asset
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
    """Validate an asset. Owner and Location are required.
    Returns (name, serial, owner, location, error_response_or_None)."""
    name = re.sub(r"\s+", " ", (data.get("name") or "")).strip()
    serial = (data.get("serial") or "").strip()
    owner_raw = (data.get("owner") or "").strip()
    location = re.sub(r"\s+", " ", (data.get("location") or "")).strip()

    def fail(message, *fields):
        return None, None, None, None, (jsonify({"message": message, "fields": list(fields)}), 400)

    missing = [(f, label) for f, label, value in (
        ("name", "Item Name", name), ("serial", "Serial Number", serial),
        ("owner", "Owner", owner_raw), ("location", "Location", location)) if not value]
    if len(missing) > 1:
        labels = [l for _, l in missing]
        joined = labels[0] if len(labels) == 1 else ", ".join(labels[:-1]) + " and " + labels[-1]
        return fail(f"{joined} are required.", *[f for f, _ in missing])
    if missing:
        return fail(f"{missing[0][1]} is required.", missing[0][0])
    if len(name) > NAME_MAX:
        return fail(f"Item Name must be at most {NAME_MAX} characters.", "name")
    serial = normalize_serial(serial)  # stored in upper case
    if not is_valid_serial(serial):
        return fail(f"Serial Number must be {SERIAL_RULE}.", "serial")
    owner = owner_resolver()(owner_raw)
    if len(owner) > OWNER_MAX:
        return fail(f"Owner must be at most {OWNER_MAX} characters.", "owner")
    if len(location) > LOCATION_MAX:
        return fail(f"Location must be at most {LOCATION_MAX} characters.", "location")
    return name, serial, owner, location, None


def _duplicate_response(duplicate):
    return jsonify({
        "message": f'This Serial Number is already registered for "{duplicate.name}".',
        "fields": ["serial"],
    }), 409


@assets_bp.route("/api/assets", methods=["POST"])
@login_required
@roles_required(*ALLOWED_ROLES)
def api_create_asset():
    name, serial, owner, location, error = _parse_asset_payload(request.get_json(silent=True) or {})
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
        owner=owner,
        location=location,
        created_by_id=session.get("user_id"),
    )
    db.session.add(asset)
    # Earlier scans of this serial (when it was not registered) are outdated now
    purge_scans(serial_keys={key})
    try:
        db.session.commit()
    except IntegrityError:  # two people adding the same serial at once
        db.session.rollback()
        return jsonify({"message": "This Serial Number is already registered.", "fields": ["serial"]}), 409

    return jsonify({"message": "Asset added successfully.", "asset": asset.to_dict(), **_scan_state()}), 201


@assets_bp.route("/api/assets/<int:asset_id>", methods=["PUT"])
@login_required
@roles_required(*ALLOWED_ROLES)
def api_update_asset(asset_id):
    asset = db.session.get(PvAsset, asset_id)
    if asset is None:
        return jsonify({"message": "Asset not found."}), 404

    name, serial, owner, location, error = _parse_asset_payload(request.get_json(silent=True) or {})
    if error:
        return error

    key = serial_key(serial)
    duplicate = PvAsset.query.filter(PvAsset.serial_key == key, PvAsset.id != asset.id).first()
    if duplicate:
        return _duplicate_response(duplicate)

    # Any change (name, serial, owner or location) means the earlier scan no
    # longer describes this asset: it goes back to "Not Checked", its scan
    # records are removed (so the Not PV count and Recent scans follow), and
    # it has to be scanned again -- the same result as a Replace import.
    old_key = asset.serial_key
    changed = (
        name != asset.name
        or key != asset.serial_key
        or owner != (asset.owner or "")
        or location != (asset.location or "")
    )
    asset.name = name
    asset.serial_number = serial
    asset.serial_key = key
    asset.owner = owner
    asset.location = location
    if changed:
        asset.scan_status = "pending"
        asset.scanned_at = None
        asset.scanned_by_id = None
        purge_scans(asset_ids={asset.id}, serial_keys={old_key, key})

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "This Serial Number is already registered.", "fields": ["serial"]}), 409

    return jsonify({
        "message": "Asset updated successfully." if not changed else "Asset updated. Scan it again to verify it.",
        "asset": asset.to_dict(),
        "reset_scan": changed,
        "old_serial": old_key,
        **_scan_state(),
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

    key = serial_key(raw_serial)
    if not key:
        return jsonify({"message": "Serial Number is required."}), 400
    if len(raw_serial) > 120:
        return jsonify({"message": "Scanned value is too long."}), 400

    now = datetime.utcnow()
    user_id = session.get("user_id")
    valid_format = is_valid_serial(key)

    # Scanning uses the Serial Number ONLY. Results:
    #   invalid  - not 4 letters + 8 digits (never looked up, NOT recorded)
    #   unknown  - valid format, but not in the list OR owned by another team
    #   match    - registered asset whose Owner is PV (marked Verified)
    asset = PvAsset.query.filter_by(serial_key=key).first() if valid_format else None

    already_scanned = False
    not_pv = False
    if not valid_format:
        result = "invalid"
    elif asset is None:
        result = "unknown"
    elif (asset.owner or "").strip().lower() != DEFAULT_OWNER.lower():
        # Registered, but owned by another team (QA, SQA, ...): not a PV asset,
        # so it is NOT marked Verified (scan_status stays as it is). The time
        # and the user are still recorded on the asset as proof of the scan.
        result = "unknown"
        not_pv = True
        asset.scanned_at = now
        asset.scanned_by_id = user_id
    else:
        already_scanned = asset.scan_status != "pending"
        result = "match"
        asset.scan_status = result
        asset.scanned_at = now
        asset.scanned_by_id = user_id

    # A badly formatted serial is only reported back: it is not a scan of
    # anything, so it is not saved, not counted and not in Recent scans.
    if result != "invalid":
        db.session.add(PvAssetScan(
            asset_id=asset.id if asset else None,
            scanned_serial=raw_serial,
            input_name=None,
            result=result,
            scanned_by_id=user_id,
            scanned_at=now,
        ))
        db.session.commit()

    return jsonify({
        "result": result,
        "valid_format": valid_format,
        "serial_rule": SERIAL_RULE,
        "already_scanned": already_scanned,
        "asset": asset.to_dict() if asset else None,
        "not_pv": not_pv,
        "unknown_count": _unknown_count(),
        "history": _history(),
    })


# ==================== Import from Excel ====================
#
# POST /api/assets/import  (multipart: file, mode, dry_run, resolutions)
#   dry_run=1  -> only analyse the file and report what would happen
#   otherwise  -> apply it. The file is parsed again here, so the user reviews
#                 and applies exactly the same result.
#   mode=merge   keep current assets, add new ones, resolve name conflicts
#   mode=replace delete ALL current assets (+ scan results) and use the file

@assets_bp.route("/api/assets/import/template", methods=["GET"])
@login_required
@roles_required(*ALLOWED_ROLES)
def api_import_template():
    return send_file(
        build_template_workbook(),
        as_attachment=True,
        download_name="pv-assets-template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@assets_bp.route("/api/assets/import", methods=["POST"])
@login_required
@roles_required(*ALLOWED_ROLES)
def api_import_assets():
    mode = (request.form.get("mode") or "merge").strip().lower()
    if mode not in ("merge", "replace"):
        return jsonify({"message": "Invalid import mode. Choose Merge or Replace."}), 400
    dry_run = request.form.get("dry_run") == "1"

    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"message": "Please choose an Excel file (.xlsx) first."}), 400
    if not upload.filename.lower().endswith(".xlsx"):
        return jsonify({"message": "Only .xlsx files are supported. In Excel, use Save As > Excel Workbook (.xlsx)."}), 400
    data = upload.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        return jsonify({"message": "The file is too large (maximum 3 MB)."}), 413

    try:
        rows = parse_assets_workbook(BytesIO(data))
    except ImportFormatError as exc:
        return jsonify({"message": str(exc)}), 400

    existing = {a.serial_key: {"name": a.name, "owner": a.owner or "", "location": a.location or ""}
                for a in PvAsset.query.all()}
    analysis = analyze_rows(rows, mode, existing)

    if dry_run:
        return jsonify({"mode": mode, "analysis": analysis, "current_count": len(existing)})

    # ---- apply ----
    try:
        resolutions = json.loads(request.form.get("resolutions") or "{}")
        if not isinstance(resolutions, dict):
            raise ValueError
    except ValueError:
        return jsonify({"message": "Invalid conflict choices."}), 400

    # Every conflict needs a full record (name, owner, location) to keep
    chosen = {}
    unresolved = []
    for conflict in analysis["conflicts"]:
        serial = conflict["serial"]
        raw = resolutions.get(serial)
        if not isinstance(raw, dict):
            unresolved.append(serial)
            continue
        final = {
            "name": collapse_spaces(str(raw.get("name") or "")),
            "owner": collapse_spaces(str(raw.get("owner") or "")),
            "location": collapse_spaces(str(raw.get("location") or "")),
        }
        if not all(final.values()):
            unresolved.append(serial)
        elif len(final["name"]) > NAME_MAX:
            return jsonify({"message": f"Item Name for {serial} must be at most {NAME_MAX} characters."}), 400
        elif len(final["owner"]) > OWNER_MAX:
            return jsonify({"message": f"Owner for {serial} must be at most {OWNER_MAX} characters."}), 400
        elif len(final["location"]) > LOCATION_MAX:
            return jsonify({"message": f"Location for {serial} must be at most {LOCATION_MAX} characters."}), 400
        else:
            chosen[serial] = final
    if unresolved:
        return jsonify({"message": "Some conflicts have not been resolved yet.", "unresolved": unresolved}), 409

    if not analysis["new"] and not analysis["conflicts"]:
        if mode == "replace":
            return jsonify({"message": "The file has no valid assets, so nothing was replaced."}), 400
        return jsonify({"message": "Nothing to import: no new assets or changes were found in the file."}), 400

    # In Replace mode the old assets (and their owners) are deleted first, so
    # the owners of the file start from scratch.
    resolve_owner = owner_resolver() if mode == "merge" else owner_resolver_empty()

    user_id = session.get("user_id")
    result = {
        "added": 0, "updated": 0, "kept": 0,
        "unchanged": len(analysis["unchanged"]),
        "skipped": len(analysis["invalid"]),
        "deleted": 0,
    }

    try:
        if mode == "replace":
            result["deleted"] = PvAsset.query.count()
            PvAssetScan.query.delete()
            PvAsset.query.delete()
            db.session.flush()
            current = {}
        else:
            current = {a.serial_key: a for a in PvAsset.query.all()}

        touched_ids, touched_keys = set(), set()

        for item in analysis["new"]:
            db.session.add(PvAsset(name=item["name"], serial_number=item["serial"],
                                   serial_key=item["serial"], created_by_id=user_id,
                                   owner=resolve_owner(item["owner"]), location=item["location"]))
            touched_keys.add(item["serial"])
            result["added"] += 1

        for conflict in analysis["conflicts"]:
            serial = conflict["serial"]
            final = chosen[serial]
            owner = resolve_owner(final["owner"])
            asset = current.get(serial)
            if asset is None:
                db.session.add(PvAsset(name=final["name"], serial_number=serial,
                                       serial_key=serial, created_by_id=user_id,
                                       owner=owner, location=final["location"]))
                touched_keys.add(serial)
                result["added"] += 1
            elif (name_key(final["name"]), name_key(owner), name_key(final["location"])) == (
                name_key(asset.name), name_key(asset.owner), name_key(asset.location)
            ):
                result["kept"] += 1  # chose the current data: nothing changes
            else:
                asset.name = final["name"]
                asset.owner = owner
                asset.location = final["location"]
                # The old verification described the old data -> scan again
                asset.scan_status = "pending"
                asset.scanned_at = None
                asset.scanned_by_id = None
                touched_ids.add(asset.id)
                touched_keys.add(serial)
                result["updated"] += 1

        if mode == "merge":
            purge_scans(asset_ids=touched_ids, serial_keys=touched_keys)

        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Another user changed the asset list at the same time. Please try the import again."}), 409

    parts = [f"{result['added']} added"]
    if result["updated"]:
        parts.append(f"{result['updated']} updated")
    if result["kept"]:
        parts.append(f"{result['kept']} kept as is")
    if result["unchanged"]:
        parts.append(f"{result['unchanged']} unchanged")
    if result["skipped"]:
        parts.append(f"{result['skipped']} invalid row{'s' if result['skipped'] != 1 else ''} skipped")
    if mode == "replace":
        parts.append(f"{result['deleted']} old asset{'s' if result['deleted'] != 1 else ''} deleted")
    label = "Replace" if mode == "replace" else "Merge"
    return jsonify({"message": f"{label} complete: " + ", ".join(parts) + ".", "result": result})
