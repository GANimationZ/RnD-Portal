"""Seeds two demo accounts (Super Admin + QA Admin) so the User
Management flow can be tried immediately. No Issue/KPI/Tool dummy data --
all of that comes from real usage through the UI.

Display names are derived from the emails (see library/naming.py):
super.admin@... -> "Super Admin", qa.admin@... -> "Qa Admin".
Log in with the EMAIL.

Usage:
    from library.seed import seed_dummy_data
    with app.app_context():
        db.create_all()
        seed_dummy_data()   # idempotent, no-op if users already exist
"""

from datetime import datetime

from library.extensions import db
from library.models import User
from library.naming import name_from_email

USER_SEED = [
    {
        "email": "super.admin@rndportal.local",
        "password": "SuperAdmin123",
        "role": "Super Admin",
    },
    {
        "email": "qa.admin@rndportal.local",
        "password": "AdminQA12345",
        "role": "Admin",
    },
]


def seed_users():
    if User.query.first():
        return

    for spec in USER_SEED:
        user = User(
            username=name_from_email(spec["email"]),
            email=spec["email"],
            role=spec["role"],
            approved_at=datetime.utcnow(),
        )
        user.set_password(spec["password"])
        db.session.add(user)

    db.session.commit()


def seed_dummy_data():
    seed_users()
