"""TV Design Concept blueprint: a searchable library of design entries
(serial number / production / origin) each with attached files (images,
PDF, Word, Excel, PowerPoint)."""

from flask import Blueprint, jsonify, render_template, request, session

from library.auth import login_required
from library.extensions import db
import os

from library.files import get_upload_dir, is_allowed, save_upload, get_file_type
from library.models import TvDesignAsset, TvDesignAttachment

tv_design_bp = Blueprint("tv_design", __name__, url_prefix="/workspace/tv-design-concept")


@tv_design_bp.route("", methods=["GET"])
@login_required
def index():
    return render_template(
        "workspace/tv_design_concept.html",
        active_nav="analyse",
        username=session.get("username"),
    )


@tv_design_bp.route("/api/assets", methods=["GET"])
@login_required
def api_list_assets():
    query = TvDesignAsset.query
    search = (request.args.get("q") or "").strip()

    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                TvDesignAsset.serial_number.ilike(like),
                TvDesignAsset.production.ilike(like),
                TvDesignAsset.origin.ilike(like),
                TvDesignAsset.title.ilike(like),
            )
        )

    assets = query.order_by(TvDesignAsset.id.desc()).all()
    return jsonify({"assets": [a.to_dict() for a in assets]})


@tv_design_bp.route("/api/assets", methods=["POST"])
@login_required
def api_create_asset():
    title = (request.form.get("title") or "").strip()
    serial_number = (request.form.get("serial_number") or "").strip()
    production = (request.form.get("production") or "").strip()
    origin = (request.form.get("origin") or "").strip()
    notes = (request.form.get("notes") or "").strip()
    files = request.files.getlist("attachments")

    if not title or not serial_number:
        return jsonify({"message": "Title and Serial Number are required."}), 400

    for file in files:
        if file and file.filename and not is_allowed(file.filename):
            return jsonify({
                "message": f'File "{file.filename}" has an unsupported format. '
                           "Use an image, PDF, Word, Excel, or PowerPoint file."
            }), 400

    asset = TvDesignAsset(
        title=title,
        serial_number=serial_number,
        production=production or None,
        origin=origin or None,
        notes=notes or None,
        created_by_id=session.get("user_id"),
    )
    db.session.add(asset)
    db.session.flush()

    for file in files:
        if not (file and file.filename):
            continue
        filename = save_upload(file, "tv-design", "tv")
        db.session.add(TvDesignAttachment(
            asset_id=asset.id,
            filename=filename,
            original_name=file.filename,
            file_type=get_file_type(file.filename),
        ))

    db.session.commit()
    return jsonify({"message": "Entry saved successfully.", "asset": asset.to_dict()}), 201


@tv_design_bp.route("/api/assets/<int:asset_id>", methods=["DELETE"])
@login_required
def api_delete_asset(asset_id):
    asset = TvDesignAsset.query.get_or_404(asset_id)

    # Attachment rows cascade-delete with the asset, but the uploaded files
    # themselves live on disk and are not tracked by the DB foreign key, so
    # they have to be removed explicitly or they become orphaned "sampah"
    # in static/assets/uploads/tv-design/.
    upload_dir = get_upload_dir("tv-design")
    for attachment in asset.attachments:
        filepath = os.path.join(upload_dir, attachment.filename)
        if os.path.exists(filepath):
            os.remove(filepath)

    db.session.delete(asset)
    db.session.commit()
    return jsonify({"message": "Entry deleted successfully."})
