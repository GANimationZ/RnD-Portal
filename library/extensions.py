"""
Instance ekstensi Flask yang dipakai bareng oleh app.py & seluruh blueprint
(mis. library/workspace/kpi_dashboard). Dipisah ke file sendiri supaya
tidak ada circular import antara app.py <-> models.py <-> routes.py.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
