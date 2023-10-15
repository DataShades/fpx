from __future__ import annotations

import contextlib

from fpx.exception import NotAuthenticatedError
from fpx.model import Client
from fpx.types import App, Request, Response


def authentication(request: Request):
    """Identify user using HTTP headers."""
    client = None
    id_: str | None = (
        request.headers.get("x-fpx-authorize")
        or request.headers.get("authorization")
        or request.headers.get("authorize")
    )

    if id_:
        client = request.ctx.db.get(Client, id_)

    if (
        not client
        and request.route
        and getattr(request.route.ctx, "requires_client", False)
    ):
        raise NotAuthenticatedError(
            {"access": "Only clients authorized to use this endpoint"},
        )

    request.ctx.client = client


def db_session(request: Request):
    """Initialize DB session."""
    request.ctx.db = request.app.ctx.db_session()


def db_session_close(request: Request, response: Response):
    # DB session is not initialized in non-existing routes
    with contextlib.suppress(AttributeError):
        request.ctx.db.close()


def add_middlewares(app: App):
    app.on_request(db_session)
    app.on_request(authentication)

    app.on_response(db_session_close)
