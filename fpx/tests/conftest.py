from __future__ import annotations

import factory
import pytest
from aioresponses import aioresponses
from pytest_factoryboy import register
from sanic_testing import TestManager
from sanic_testing.reusable import ReusableClient

from fpx import model as m
from fpx.app import make_app
from fpx.cli.db import _up

from . import settings


@pytest.fixture()
def non_mocked_hosts() -> list:
    return ["localhost", "127.0.0.1"]


@pytest.fixture()
def rmock_aiohttp():
    """Response factory for aiohttp."""
    with aioresponses() as r:

        def mock(url, body="", headers=None):
            r.add(url=url, body=body, headers=headers)

        yield mock


@pytest.fixture()
def rmock_httpx(httpx_mock):
    """Response factory for httpx."""

    def mock(url, body="", headers=None):
        httpx_mock.add_response(url=url, content=body, headers=headers)

    return mock


@pytest.fixture()
def rmock(transport_name, rmock_httpx, rmock_aiohttp):
    """Mock async response.

    This fixture produce a different mock factory, depending on the value of
    `transport_name` fixture.
    """
    if transport_name == "aiohttp":
        return rmock_aiohttp

    if transport_name == "httpx":
        return rmock_httpx

    msg = f"Unsupported transport {transport_name}"
    raise AssertionError(msg)


@pytest.fixture(params=["aiohttp", "httpx"])
def transport_name(request):
    """Run test once for each name of supported transport."""
    return request.param


@pytest.fixture()
def all_transports(monkeypatch, transport_name):
    """Run tests with all available transports.

    Apply this fixture before `app`/`reusable_client`
    """
    monkeypatch.setenv("FPX_FPX_TRANSPORT", transport_name)


@pytest.fixture()
def app(monkeypatch, tmpdir):
    """Ready-to-use FPX application"""
    monkeypatch.setenv("FPX_CONFIG", settings.__file__)
    monkeypatch.setenv("FPX_DB_URL", f"sqlite:///{tmpdir}/fpx.db")
    application = make_app()
    TestManager(application)
    _up(application)
    return application


@pytest.fixture()
def test_client(app):
    """Test client that creates a new application for each request."""
    return app.test_client


@pytest.fixture()
def url_for(app):
    """URL generator."""
    return app.url_for


@pytest.fixture()
def reusable_client(app):
    """Test client that reuse application during the test."""

    client = ReusableClient(app)
    with client:
        yield client


@pytest.fixture()
def rc(reusable_client):
    """Shorthand for `reusable_cleint`"""
    return reusable_client


@pytest.fixture()
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

    type = "zip"
    content = '["http://example.com"]'
