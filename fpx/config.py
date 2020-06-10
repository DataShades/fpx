from sanic import Sanic
from logging.config import dictConfig
from fpx.model import make_db_session


def configure_app(app: Sanic):
    dictConfig(app.config.LOGGING)
    make_db_session(app)
    return app
