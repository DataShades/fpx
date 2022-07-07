import pytest
from fpx.app import make_app
from fpx.cli.db import _up
import factory
from pytest_factoryboy import register
from sanic_testing import TestManager
from . import settings
from .. import model as m


@pytest.fixture
def app(monkeypatch, tmpdir):
    monkeypatch.setenv("FPX_CONFIG", settings.__file__)
    db_path = f"sqlite:///{tmpdir}/fpx.db"
    monkeypatch.setenv('FPX_DB_URL', db_path)
    application = make_app()

    TestManager(application)

    _up(application)
    yield application


@pytest.fixture
def db(app):
    return app.ctx.DbSession()


@register
class TicketFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = m.Ticket
        sqlalchemy_session = m.scoped_session
        sqlalchemy_session_persistence = "commit"

    type = "url"
    content = factory.Dict()
