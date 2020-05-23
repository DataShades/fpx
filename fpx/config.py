from sanic import Sanic
from logging.config import dictConfig
from fpx.model import make_app_session


def configure_app(app: Sanic):
    dictConfig(app.config.LOGGING)
    make_app_session(app)
    return app
