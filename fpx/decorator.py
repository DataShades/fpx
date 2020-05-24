from functools import wraps
from fpx.model import Client
from sanic import response


def client_only(handler):
    @wraps(handler)
    async def wrapper(request, *args, **kwargs):
        id = request.headers.get("authorize")
        client = request.ctx.db.query(Client).get(id)
        if client is None:
            return response.json({
                'error': "Only clients authorized to use this endpoint"
            }, 401)
        return handler(request, *args, **kwargs)

    return wrapper
