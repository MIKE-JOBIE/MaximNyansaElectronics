import pytest
from flask import g, has_app_context
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db
from config import TestingConfig


class IsolatedUserLoaderClient(FlaskClient):
    """Avoid leaking Flask-Login's g cache across requests in a preserved app context."""
    def open(self, *args, **kwargs):
        if has_app_context():
            g.pop("_login_user", None)
        try:
            return super().open(*args, **kwargs)
        finally:
            if has_app_context():
                g.pop("_login_user", None)


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    app.test_client_class = IsolatedUserLoaderClient
    return app.test_client()
