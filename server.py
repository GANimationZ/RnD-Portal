import logging
from waitress import serve
from app import app
from library.extensions import db
from library.seed import seed_dummy_data

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_dummy_data()

    serve(app, host="0.0.0.0", port=5000, threads=8)
