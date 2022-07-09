from sanic import Sanic, response
from webargs_sanic.sanicparser import HandleValidationError
from .route import add_routes
from .config import FpxConfig
from .middleware import add_middlewares
from .context import Context


async def handle_validation_error(request, err):
    return response.json({"errors": err.exc.messages}, status=422)


def make_app():
    app = Sanic("FPX", ctx=Context(), config=FpxConfig())

    add_middlewares(app)
    add_routes(app)

    app.exception(HandleValidationError)(handle_validation_error)
    return app


def run_app(app: Sanic):
    app.run(
        host=app.config.HOST,
        port=app.config.PORT,
        debug=app.config.DEBUG,
        auto_reload=app.config.DEBUG,
    )
