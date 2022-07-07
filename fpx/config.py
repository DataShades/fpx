from sanic import Sanic
from logging.config import dictConfig
from fpx.model import make_db_session
from . import default_settings

def configure_app(app: Sanic):
    app.config.update_config(default_settings)
    app.config.load_environment_vars(prefix="FPX_", )
    app.config.update_config("${FPX_CONFIG}")

    dictConfig(app.config.LOGGING)
    make_db_session(app)
    return app
