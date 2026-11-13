import os

from library import create_app
from library.extensions import db
from library.seed import seed_dummy_data

app = create_app()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_dummy_data()

    app.run(host="0.0.0.0", port=5000, debug=os.environ.get("FLASK_DEBUG") == "0")
