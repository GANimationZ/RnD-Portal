"""Auth decorators & helpers shared across all blueprints."""

from functools import wraps

from flask import abort, redirect, request, session, url_for

# Halaman tujuan setelah login (dan tombol "Ke Halaman Utama" di halaman
# error) untuk tiap role. Role yang tidak terdaftar di sini memakai
# DEFAULT_HOME_ENDPOINT.
#
# QA (role "Admin") tidak punya akses ke KPI Dashboard, jadi landing page-nya
# Issue Monitoring -- kalau tidak, setiap login/redirect akan mentok di
# halaman yang justru ditolak untuk role tersebut.
ROLE_HOME_ENDPOINT = {
    "Admin": "issue_monitor.index",
}
DEFAULT_HOME_ENDPOINT = "main.kpi_dashboard"


def home_url(role=None):
    """URL halaman utama untuk `role` (default: role user yang sedang login)."""
    if role is None:
        role = session.get("role")
    return url_for(ROLE_HOME_ENDPOINT.get(role, DEFAULT_HOME_ENDPOINT))


def wants_json():
    """True kalau request ini dari fetch()/API dan sebaiknya dibalas JSON,
    bukan halaman HTML. Dipakai decorator di bawah dan error handler
    (library/errors.py) supaya perilakunya konsisten."""
    if request.is_json:
        return True
    path = request.path.rstrip("/")
    if "/api/" in request.path or path.endswith("/api"):
        return True
    # Client yang eksplisit lebih memilih JSON daripada HTML lewat header
    # Accept. Accept "*/*" (default fetch()) sengaja tidak dihitung.
    accepts = request.accept_mimetypes
    best = accepts.best_match(["application/json", "text/html"])
    return best == "application/json" and accepts[best] > accepts["text/html"]


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.onboard"))
        return f(*args, **kwargs)

    return decorated_function


def roles_required(*roles):
    """Use after @login_required. Kalau role tidak cocok, memicu HTTP 403
    lewat abort(). Error handler 403 (library/errors.py) yang memutuskan
    bentuk balasannya: halaman "Akses Ditolak" untuk navigasi biasa, atau
    JSON untuk API/fetch supaya frontend bisa menampilkan pesan error yang
    proper.

    Sengaja TIDAK me-redirect ke dashboard: untuk role yang ditolak dari
    dashboard itu sendiri (mis. Admin vs KPI Dashboard) redirect ke sana
    berujung redirect loop."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("main.onboard"))

            if session.get("role") not in roles:
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator
