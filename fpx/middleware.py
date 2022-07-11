from sanic import Sanic, response

from fpx.model import Client


def authentication(request):
    client = None
    id_ = request.headers.get("authorize")
    if id_:
        client = request.ctx.db.query(Client).get(id_)

    if (
        not client
        and request.route
        and getattr(request.route.ctx, "requires_client", False)
    ):
        return response.json(
            {
                "errors": {
                    "access": "Only clients authorized to use this endpoint"
                }
            },
            401,
        )
    request.ctx.client = client


def db_session(request):
    request.ctx.db = request.app.ctx.db_session()


def db_session_close(request, response):
    try:
        request.ctx.db.close()
    except AttributeError:
        # DB session is not set. Probably it's non-existing route
        pass


def add_middlewares(app: Sanic):
    app.on_request(db_session)
    app.on_request(authentication)

    app.on_response(db_session_close)
