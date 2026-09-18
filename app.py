# --- Package Import ---
import os
import secrets

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, abort
from flask_scss import Scss

from library.auth import login_required
from library.extensions import db
from library.models import User


# ---- App Setup ----
app = Flask(__name__)

Scss(app)

# ---- App Configuration ----
app.config['SECRET_KEY'] = secrets.token_hex(32)


# ---- Konfigurasi Database ----
database_url = os.environ.get(
    "DATABASE_URL",
    "sqlite:///database.db"
)

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
    if 'user_id' in session:
        return redirect(url_for('kpi_dashboard'))

    return render_template('auth/auth.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Invalid request.'}), 400

        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        retype = data.get('retype')

        if not username or not password or not email:
            return jsonify({'error': 'Please fill all the empty boxes.'}), 400

        if len(password) < 8:
            return jsonify({'error': 'Minimal 8 Characters long.'}), 400

        if password != retype:
            return jsonify({'error': 'Password does not match'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Already taken.'}), 409

        new_user = User(username=username)
        new_user.email = email
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        return jsonify({'message': f'User {username} successfully created.'}), 201

    return render_template('auth/auth.html')


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Invalid request.'}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Please fill the empty box.'}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password.'}), 401

    session['user_id'] = user.id
    session['username'] = user.username

    return jsonify({'message': f'Welcome back, {username}!'}), 200


# ---- Route Issue (Detail Issue ID = 1) ----

@login_required
def issue_detail(issue_id):
    """
    Halaman Detail Issue berdasarkan ID (misal: ID=1)
    Menampilkan data issue beserta file gambar dari static/assets/upload/
    """
    # Dummy data issue id = 1
    # Jika menggunakan model ORM, ganti bagian ini dengan query database (misal: Issue.query.get_or_404(issue_id))
    dummy_issues = {
        1: {
            "id": 1,
            "title": "Bug pada Tampilan KPI Dashboard",
            "description": "Ditemukan kesalahan render grafik saat memuat data pada resolusi layar tertentu.",
            "status": "In Progress",
            "priority": "High",
            "created_at": "2026-09-17",
            "image_filename": "issue_1.png" # File disimpan di static/assets/upload/issue_1.png
        }
    }

    issue_data = dummy_issues.get(issue_id)

    if not issue_data:
        abort(404, description="Issue tidak ditemukan")

    return render_template(
        'workspace/issue_detail.html',
        issue=issue_data,
        active_nav='issue-monitor',
        username=session.get('username')
    )


# ---- Workspace ----

@app.route('/workspace/kpi-dashboard', methods=['GET'])
@login_required
def kpi_dashboard():
    return render_template(
        'workspace/kpi_dashboard.html',
        active_nav='kpi-dashboard',
        username=session.get('username')
    )


@app.route('/workspace/tv-design-concept', methods=['GET'])
@login_required
def tv_design_concept():
    return render_template(
        'workspace/tv_design_concept.html',
        active_nav='analyse',
        username=session.get('username')
    )


@app.route('/workspace/tools', methods=['GET'])
@login_required
def tools():
    return render_template(
        'workspace/tools.html',
        active_nav='tools',
        username=session.get('username')
    )


# ---- Team ----

@app.route('/team/structure', methods=['GET'])
@login_required
def org_structure():
    return render_template(
        'team/structure.html',
        active_nav='structure',
        username=session.get('username')
    )


@app.route('/team/others', methods=['GET'])
@login_required
def team_others():
    return render_template(
        'team/others.html',
        active_nav='others',
        username=session.get('username')
    )


# ---- Logout ----

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out.'}), 200


# ---- Running and Debugging ----

if __name__ == '__main__':

    with app.app_context():
        db.create_all()
        seed_dummy_data()
        seed_dummy_issues()

    app.run(host='0.0.0.0', port=8000, debug=True)