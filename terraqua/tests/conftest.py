import pytest

from app import create_app
from config import TestConfig
from app.seed import run_seed


@pytest.fixture
def app():
    application = create_app(TestConfig)
    with application.app_context():
        run_seed()
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username, password):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )
