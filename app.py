# Imports
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import secrets

# App Setup
app = Flask(__name__)
Scss(app)

app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)

# Data Rows
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='scrypt')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('onboard'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/', methods=['GET'])
def onboard():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
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


@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    return render_template('dashboard/index.html', username=session.get('username'))


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out.'}), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)