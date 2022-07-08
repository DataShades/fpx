from sanic import Sanic, response
from sanic.handlers import ErrorHandler
from webargs_sanic.sanicparser import HandleValidationError
from .route import add_routes
from .config import FpxConfig
from .middleware import add_middlewares
from .context import Context

class FpxErrorHandler(ErrorHandler):
    def default(self, request, exception):
        if isinstance(exception, HandleValidationError):
            return response.json(exception.data["message"], exception.status_code)
        return super().default(request, exception)



def make_app():
    app = Sanic("FPX", ctx=Context(), config=FpxConfig(), error_handler=FpxErrorHandler())

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
