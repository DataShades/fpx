import pytest
from shutil import rmtree
from fpx.app import make_app
from fpx.cli.db import _up

from . import settings

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

def _engine():
    return create_engine('sqlite://',
              connect_args={'check_same_thread':False},
              poolclass=StaticPool)

@pytest.fixture
def app(monkeypatch, tmpdir):
    monkeypatch.setenv("FPX_CONFIG", settings.__file__)
    db_path = f"sqlite:///{tmpdir}/fpx.db"
    monkeypatch.setenv('FPX_DB_URL', db_path)
    application = make_app()
    application.DbSession.bind = _engine()
    _up(application)
    yield application

@pytest.fixture
def db(app):
    return app.ctx.DbSession()
