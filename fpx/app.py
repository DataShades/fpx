from sanic import Sanic, response
from webargs_sanic.sanicparser import HandleValidationError

from .config import FpxConfig
from .context import Context
from .middleware import add_middlewares
from .route import add_routes
from . import exception


async def handle_validation_error(request, err):
    return response.json({"errors": err.exc.messages}, status=422)


async def handle_fpx_error(request, err: exception.NotFound):
    return response.json({"errors": err._details}, status=err._status)


def make_app():
    app = Sanic("FPX", ctx=Context(), config=FpxConfig())

    add_middlewares(app)
    add_routes(app)

    app.exception(HandleValidationError)(handle_validation_error)
    app.exception(exception.FpxError)(handle_fpx_error)
    return app


def run_app(app: Sanic):
    app.run(
        host=app.config.HOST,
        port=app.config.PORT,
        debug=app.config.DEBUG,
        auto_reload=app.config.DEBUG,
    )
