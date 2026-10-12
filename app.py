"""WSGI entry point. App assembly (config, db, blueprints) lives in
library/__init__.py (create_app()) -- see the docstring there for why it's
split out.

Run the app:
    python app.py
Or (if you later use Gunicorn etc. in production):
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
