from functools import wraps

from flask import session, redirect, url_for, jsonify, request


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if 'user_id' not in session:
            return redirect(url_for('main.onboard'))

        return f(*args, **kwargs)

    return decorated_function


def roles_required(*roles):
    """Dipasang SETELAH @login_required (login_required duluan yang cek
    session, baru ini yang cek role) -- lihat pemakaiannya di
    library/admin/user_management/routes.py & library/workspace/issue_monitor/routes.py.

    Kalau request-nya minta HTML (buka halaman langsung di browser),
    redirect balik ke dashboard. Kalau request-nya API/JSON (fetch dari
    JS), balikin 403 JSON supaya JS bisa nampilin pesan error, bukan
    ngirim balik halaman HTML yang tidak diharapkan fetch().
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('main.onboard'))

            if session.get('role') not in roles:
                wants_json = (
                    request.is_json
                    or request.path.startswith('/admin/users/api')
                    or request.path.rstrip('/').endswith('/api')
                    or '/api/' in request.path
                )
                if wants_json:
                    return jsonify({"message": "Akses ditolak: hak akses tidak mencukupi."}), 403
                return redirect(url_for('main.kpi_dashboard'))

            return f(*args, **kwargs)

        return decorated_function

    return decorator