# --- Package Import ----
import os
import secrets
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_scss import Scss

from library.extensions import db
from library.models import User
from library.seed import seed_dummy_data
from library.workspace.kpi_dashboard.routes import kpi_dashboard_bp

# ---- App Setup ----
app = Flask(__name__)
Scss(app)
app.register_blueprint(kpi_dashboard_bp)

# ---- App Configuration ----
app.config['SECRET_KEY'] = secrets.token_hex(32)

# ---- Konfigurasi Database ----
# Persiapan migrasi SQLite -> PostgreSQL: cukup set environment variable
# DATABASE_URL, tidak perlu ubah kode apapun (model sudah pakai tipe kolom
# generik di library/models.py). Contoh untuk Postgres:
#   export DATABASE_URL="postgresql+psycopg2://user:password@host:5432/rnd_portal"
# Kalau DATABASE_URL tidak di-set, otomatis fallback ke SQLite lokal supaya
# dev environment tetap jalan tanpa setup tambahan.
database_url = os.environ.get("DATABASE_URL", "sqlite:///database.db")
if database_url.startswith("postgres://"):
    # beberapa provider (mis. Heroku) masih kasih URL dengan skema lama.
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

db.init_app(app)

# ---- Define Barrier ----
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('onboard'))
        return f(*args, **kwargs)
    return decorated_function

# ---- Web Routing ----
@app.route('/', methods=['GET'])
def onboard():
    if 'user_id' in session:
        return redirect(url_for('workspace/kpi-dashboard'))
    return render_template('auth/auth.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()

        username = data.get('username')
        password = data.get('password')
        retype = data.get('retype')

        if not username or not password:
            return jsonify({'error': 'Please fill the empty box.'}), 400

        if len(password) < 8:
            return jsonify({'error': 'Minimal 8 Characters long.'}), 400

        if password != retype:
            return jsonify({'error': 'Password does not match'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Already taken.'}), 409

        new_user = User(username=username)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        return jsonify({'message': f'User {username} successfully created.'}), 201

    return render_template('auth/auth.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
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

@app.route('/workspace/kpi-dashboard', methods=['GET'])
@login_required
def kpi_dashboard():
    return render_template('workspace/kpi_dashboard.html', active_nav='kpi-dashboard', username=session.get('username'))

@app.route('/workspace/tv-design-concept', methods=['GET'])
@login_required
def tv_design_concept():
    return render_template('workspace/tv_design_concept.html', active_nav='analyse', username=session.get('username'))

@app.route('/workspace/issue-monitor', methods=['GET'])
@login_required
def issue_monitor():
    all_users = User.query.all()

    return render_template('workspace/issue_monitor.html', active_nav='issue-monitor', username=session.get('username'), users=all_users)

@app.route('/workspace/tools', methods=['GET'])
@login_required
def tools():
    return render_template('workspace/tools.html', active_nav='tools', username=session.get('username'))

@app.route('/team/structure', methods=['GET'])
@login_required
def org_structure():
    return render_template('team/structure.html', active_nav='structure', username=session.get('username'))

@app.route('/team/others', methods=['GET'])
@login_required
def team_others():
    return render_template('team/others.html', active_nav='others', username=session.get('username'))

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out.'}), 200

# ---- Running and Debugging ----
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_dummy_data()
    app.run(debug=True)
