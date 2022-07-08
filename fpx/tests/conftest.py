import pytest
from fpx.app import make_app
from fpx.cli.db import _up
import factory
from pytest_factoryboy import register
# from sanic_testing import TestManager
from sanic_testing.reusable import ReusableClient
from . import settings
from .. import model as m


@pytest.fixture
def app(monkeypatch, tmpdir):
    monkeypatch.setenv("FPX_CONFIG", settings.__file__)
    monkeypatch.setenv('FPX_DB_URL', f"sqlite:///{tmpdir}/fpx.db")
    application = make_app()

    _up(application)
    yield application

@pytest.fixture
def test_client(app):
    return app.test_client

@pytest.fixture
def url_for(app):
    return app.url_for

@pytest.fixture
def reusable_client(app):
    client = ReusableClient(app)
    with client:
        yield client


@pytest.fixture
def db(app):
    return app.ctx.db_session()


@register
class ClientFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = m.Client
        sqlalchemy_session = m.Session
        sqlalchemy_session_persistence = "commit"

    name = factory.Faker("username")

@register
class TicketFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = m.Ticket
        sqlalchemy_session = m.Session
        sqlalchemy_session_persistence = "commit"

    type = "url"
    content = '[{"url": "http://example.com"}]'
    # options
    # is_available
    # created_at
