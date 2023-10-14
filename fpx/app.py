from sanic import Sanic, response
from sanic.worker.loader import AppLoader
from webargs_sanic.sanicparser import HandleValidationError

from . import exception
from .config import FpxConfig
from .context import Context
from .middleware import add_middlewares
from .route import add_routes


async def handle_validation_error(request, err):
    return response.json({"errors": err.exc.messages}, status=422)


async def handle_fpx_error(request, err: exception.NotFoundError):
    return response.json({"errors": err._details}, status=err._status)


def make_app():
    app = Sanic("FPX", ctx=Context(), config=FpxConfig())

    add_middlewares(app)
    add_routes(app)

    app.exception(HandleValidationError)(handle_validation_error)
    app.exception(exception.FpxError)(handle_fpx_error)
    return app


loader = AppLoader(factory=make_app)


def run_app(app: Sanic):
    app.prepare(
        host=app.config.HOST,
        port=app.config.PORT,
        dev=app.config.DEBUG,
    )

    Sanic.serve(app, app_loader=loader)
