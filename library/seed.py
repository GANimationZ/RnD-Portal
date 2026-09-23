"""Seeds two demo accounts (Super Admin + QA Admin) so the User
Management flow can be tried immediately. No Employee/Issue/KPI dummy
data -- all of that comes from real usage through the UI.

Usage:
    from library.seed import seed_dummy_data
    with app.app_context():
        db.create_all()
        seed_dummy_data()   # idempotent, no-op if users already exist
"""

from library.extensions import db
from library.models import User

# Plaintext here is fine for a demo seed -- change these via User
# Management as soon as the app is used for real.
USER_SEED = [
    {
        "username": "superadmin",
        "email": "superadmin@rndportal.local",
        "password": "SuperAdmin123",
        "role": "Super Admin",
    },
    {
        "username": "qa.admin",
        "email": "qa.admin@rndportal.local",
        "password": "AdminQA12345",
        "role": "Admin",
    },
]


def seed_users():
    if User.query.first():
        return

    for spec in USER_SEED:
        user = User(username=spec["username"], email=spec["email"], role=spec["role"])
        user.set_password(spec["password"])
        db.session.add(user)

    db.session.commit()


def seed_dummy_data():
    """Idempotent: no-op if the users table already has rows."""
    seed_users()
