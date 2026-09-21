"""
Entry point WSGI. Logic perakitan aplikasi (config, db, blueprint) ada di
library/__init__.py (create_app()) -- lihat docstring di sana untuk alasan
kenapa dipisah begini.

Menjalankan app:
    python app.py
Atau (kalau nanti pakai Gunicorn/dsb di production):
    gunicorn "app:app"
"""

from library import create_app
from library.extensions import db
from library.seed import seed_dummy_data

app = create_app()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_dummy_data()

    app.run(host="0.0.0.0", port=8000, debug=True)
