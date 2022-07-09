import factory
import pytest
from aioresponses import aioresponses
from pytest_factoryboy import register

# from sanic_testing import TestManager
from sanic_testing.reusable import ReusableClient

from fpx.app import make_app
from fpx.cli.db import _up

from .. import model as m
from . import settings


@pytest.fixture
def rmock():
    with aioresponses() as r:
        yield r


@pytest.fixture
def app(monkeypatch, tmpdir):
    """Ready-to-use FPX application"""
    monkeypatch.setenv("FPX_CONFIG", settings.__file__)
    monkeypatch.setenv("FPX_DB_URL", f"sqlite:///{tmpdir}/fpx.db")
    application = make_app()

    _up(application)
    yield application


@pytest.fixture
def test_client(app):
    """Test client that creates a new application for each request."""
    return app.test_client


@pytest.fixture
def url_for(app):
    """URL generator."""
    return app.url_for


@pytest.fixture
def reusable_client(app):
    """Test client that reuse application during the test."""

    client = ReusableClient(app)
    with client:
        yield client


@pytest.fixture
def rc(reusable_client):
    """Shorthand for `reusable_cleint`"""
    return reusable_client


@pytest.fixture
def db(app):
    """Active DB session."""
    return app.ctx.db_session()


@register
class ClientFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = m.Client
        sqlalchemy_session = m.Session
        sqlalchemy_session_persistence = "commit"

    name = factory.Faker("user_name")


@register
class TicketFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = m.Ticket
        sqlalchemy_session = m.Session
        sqlalchemy_session_persistence = "commit"

    type = "url"
    content = '["http://example.com"]'
    # options
    # is_available
    # created_at
