"""Shared Flask extension instances, used by app.py and every blueprint.
Kept in its own module to avoid circular imports between app.py, models.py,
and routes.py."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
