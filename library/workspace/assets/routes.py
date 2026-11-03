from flask import Blueprint, render_template, session

from library.auth import login_required

assets_bp = Blueprint("assets", __name__, url_prefix="/workspace/assets")


# ==================== Pages ====================

@assets_bp.route("", methods=["GET"])
@login_required
def index():
    # Tahap 1 (FrontEnd saja): halaman masih memakai data contoh di
    # static/javascript/workspace/assets.js. API & model database
    # (daftar asset PV) menyusul di tahap berikutnya.
    return render_template(
        "workspace/assets.html",
        active_nav="assets",
        username=session.get("username"),
    )
