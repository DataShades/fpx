"""Generic logic for app initialization.
"""
from sanic import Sanic
from sanic.worker.loader import AppLoader

from fpx.types import App

from . import exception, middleware, route
from .config import FpxConfig
from .context import Context


def make_app() -> Sanic[FpxConfig, Context]:
    """Initialize and setup Sanic application.

    This function used by built-in server, tests and during app initialization
    for CLI.

    """
    app = Sanic("FPX", ctx=Context(), config=FpxConfig())

    middleware.add_middlewares(app)
    route.add_routes(app)
    exception.add_handlers(app)

    return app


loader = AppLoader(factory=make_app)


def run_app(app: App):
    """Serve app via Sanic web-server."""
    app.prepare(
        host=app.config.HOST,
        port=app.config.PORT,
        dev=app.config.DEBUG,
    )

    Sanic.serve(app, app_loader=loader)
