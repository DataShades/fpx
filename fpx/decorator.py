from functools import wraps
from fpx.model import Client
from sanic import exceptions


def client_only(handler):
    @wraps(handler)
    async def wrapper(request, *args, **kwargs):
        id = request.headers.get("authorize")
        client = request.ctx.db.query(Client).get(id)
        if client is None:
            raise exceptions.Unauthorized(
                "Only clients authorized to use this endpoint"
            )
        return handler(request, *args, **kwargs)

    return wrapper
