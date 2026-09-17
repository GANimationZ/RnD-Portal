# --- Package Import ---
import os
import secrets

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_scss import Scss

from library.auth import login_required
from library.extensions import db
from library.models import User
from library.seed import seed_dummy_data, seed_dummy_issues
from library.workspace.kpi_dashboard.routes import kpi_dashboard_bp
from library.workspace.issue_monitor.routes import issue_monitor_bp


# ---- App Setup ----
app = Flask(__name__)

Scss(app)

app.register_blueprint(kpi_dashboard_bp)
app.register_blueprint(issue_monitor_bp)


# ---- App Configuration ----
app.config['SECRET_KEY'] = secrets.token_hex(32)


# ---- Konfigurasi Database ----
# Persiapan migrasi SQLite -> PostgreSQL:
# cukup set environment variable DATABASE_URL.
#
# Jika DATABASE_URL tidak di-set, aplikasi akan menggunakan
# SQLite lokal: database.db

database_url = os.environ.get(
    "DATABASE_URL",
    "sqlite:///database.db"
)

# Beberapa provider masih menggunakan skema postgres://
if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True
}

db.init_app(app)


# ---- Web Routing ----

@app.route('/', methods=['GET'])
def onboard():
    """
    Halaman awal / login.
    Jika user sudah login, arahkan ke KPI Dashboard.
    """
    if 'user_id' in session:
        return redirect(url_for('kpi_dashboard'))

    return render_template('auth/auth.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registrasi user baru.
    """
    if request.method == 'POST':
        data = request.get_json()

        # Jika request tidak memiliki JSON
        if not data:
            return jsonify({
                'error': 'Invalid request.'
            }), 400

        username = data.get('username')
        password = data.get('password')
        retype = data.get('retype')

        # Validasi input kosong
        if not username or not password:
            return jsonify({
                'error': 'Please fill the empty box.'
            }), 400

        # Validasi panjang password
        if len(password) < 8:
            return jsonify({
                'error': 'Minimal 8 Characters long.'
            }), 400

        # Validasi password
        if password != retype:
            return jsonify({
                'error': 'Password does not match'
            }), 400

        # Cek username
        if User.query.filter_by(username=username).first():
            return jsonify({
                'error': 'Already taken.'
            }), 409

        # Buat user baru
        new_user = User(username=username)

        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            'message': f'User {username} successfully created.'
        }), 201

    return render_template('auth/auth.html')


@app.route('/login', methods=['POST'])
def login():
    """
    Login user.
    """
    data = request.get_json()

    if not data:
        return jsonify({
            'error': 'Invalid request.'
        }), 400

    username = data.get('username')
    password = data.get('password')

    # Validasi input
    if not username or not password:
        return jsonify({
            'error': 'Please fill the empty box.'
        }), 400

    # Cari user berdasarkan username
    user = User.query.filter_by(
        username=username
    ).first()

    # Cek user dan password
    if not user or not user.check_password(password):
        return jsonify({
            'error': 'Invalid username or password.'
        }), 401

    # Simpan informasi user ke session
    session['user_id'] = user.id
    session['username'] = user.username

    return jsonify({
        'message': f'Welcome back, {username}!'
    }), 200


# ---- Workspace ----

@app.route('/workspace/kpi-dashboard', methods=['GET'])
@login_required
def kpi_dashboard():
    """
    KPI Dashboard.
    """
    return render_template(
        'workspace/kpi_dashboard.html',
        active_nav='kpi-dashboard',
        username=session.get('username')
    )


@app.route('/workspace/tv-design-concept', methods=['GET'])
@login_required
def tv_design_concept():
    """
    TV Design Concept.
    """
    return render_template(
        'workspace/tv_design_concept.html',
        active_nav='analyse',
        username=session.get('username')
    )


@app.route('/workspace/tools', methods=['GET'])
@login_required
def tools():
    """
    Tools.
    """
    return render_template(
        'workspace/tools.html',
        active_nav='tools',
        username=session.get('username')
    )


# ---- Team ----

@app.route('/team/structure', methods=['GET'])
@login_required
def org_structure():
    """
    Team Structure.
    """
    return render_template(
        'team/structure.html',
        active_nav='structure',
        username=session.get('username')
    )


@app.route('/team/others', methods=['GET'])
@login_required
def team_others():
    """
    Team Others.
    """
    return render_template(
        'team/others.html',
        active_nav='others',
        username=session.get('username')
    )


# ---- Logout ----

@app.route('/logout', methods=['POST'])
def logout():
    """
    Logout user dan hapus session.
    """
    session.clear()

    return jsonify({
        'message': 'Logged out.'
    }), 200


# ---- Running and Debugging ----

if __name__ == '__main__':

    with app.app_context():

        # Membuat tabel database jika belum ada
        db.create_all()

        # Mengisi dummy data
        seed_dummy_data()
        seed_dummy_issues()

    # Menjalankan Flask
    app.run(debug=True)