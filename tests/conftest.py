import pytest

from app import create_app
from app.db import db as _db


@pytest.fixture
def app():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    yield app


@pytest.fixture
def db(app):
    with app.app_context():
        yield _db
        _db.session.remove()
