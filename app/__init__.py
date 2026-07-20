import os
from flask import Flask
from sqlalchemy import event

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

        @event.listens_for(db.engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    from app.routes.rooms import rooms_bp
    app.register_blueprint(rooms_bp)

    return app