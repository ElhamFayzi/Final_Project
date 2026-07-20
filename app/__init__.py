import os
from flask import Flask
from app.db import db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    os.makedirs(app.instance_path, exist_ok=True)
    app.config.setdefault(
        "SQLALCHEMY_DATABASE_URI",
        f"sqlite:///{os.path.join(app.instance_path, 'petty_court.db')}",
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        from app import models  
        db.create_all()

    return app
