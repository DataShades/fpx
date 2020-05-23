from sanic import Sanic
from sanic_cors import CORS


from .route import add_routes
from .config import configure_app
from .middleware import add_middlewares
from . import default_settings

def make_app():
    app = Sanic("fdx", load_env="FPX_")
    app.config.from_object(default_settings)
    app.config.from_envvar("FPX_CONFIG")
    CORS(app)
    configure_app(app)
    add_middlewares(app)
    add_routes(app)
    return app


def run_app():
    app = make_app()
    app.run(
        host=app.config.HOST, port=app.config.PORT, debug=app.config.DEBUG,
    )
