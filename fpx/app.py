from sanic import Sanic

from .route import add_routes
from .config import configure_app
from .middleware import add_middlewares

def make_app():
    app = Sanic("FPX")

    configure_app(app)
    add_middlewares(app)
    add_routes(app)

    return app


def run_app(app: Sanic):
    app.run(
        host=app.config.HOST,
        port=app.config.PORT,
        debug=app.config.DEBUG,
        auto_reload=app.config.DEBUG
    )
