from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from sanic import Blueprint, response
from sanic.exceptions import WebsocketClosed
from sanic.server.websockets.impl import WebsocketImplProtocol
from sqlalchemy.orm.query import Query
from webargs_sanic.sanicparser import use_kwargs

from fpx import exception, schema, utils
from fpx.model import Ticket
from fpx.pipes import Pipe
from fpx.types import Request

log = logging.getLogger(__name__)

ticket = Blueprint("ticket", url_prefix="/ticket")


@ticket.get("/")
@use_kwargs(schema.TicketIndex(), location="query")
async def index(request: Request, page: int) -> response.HTTPResponse:
    limit = 10
    base: Query[Ticket] = request.ctx.db.query(Ticket)
    q = base.limit(limit).offset(limit * page - limit)
    return response.json(
        {
            "page": page,
            "count": base.count(),
            "tickets": [t.for_json() for t in q],
        },
    )


@ticket.route("/generate", methods=["POST"], ctx_requires_client=True)
@use_kwargs(schema.TicketGenerate(), location="json")
async def generate(
    request: Request,
    type: str,
    items: Any,
    options: dict[str, Any],
) -> response.HTTPResponse:
    ticket = Ticket(type=type, items=items, options=options)
    if request.app.config.FPX_NO_QUEUE:
        ticket.is_available = True

    request.ctx.db.add(ticket)
    request.ctx.db.commit()

    return response.json(ticket.for_json(include_id=True))


@ticket.route("/<id>/download")
async def download(request: Request, id: str):
    db = request.ctx.db
    ticket = db.get(Ticket, id)

    if ticket is None:
        raise exception.NotFoundError({"id": "Ticket not found"})

    if not ticket.is_available:
        raise exception.NotAuthorizedError(
            {"access": "You must wait untill download is available"},
        )

    response = await request.respond()
    if not response:
        raise ValueError("response")

    async with Pipe.choose(ticket, request) as pipe:
        response.content_type = pipe.content_type()
        filename = pipe.filename()
        response.headers["content-disposition"] = f'attachment; filename="{filename}"'
        log.info(
            "Prepare for streaming %s using %s pipe",
            filename,
            type(pipe).__name__,
        )
        with utils.ActiveDownload(request.app.ctx.active_downloads, id):
            db.delete(ticket)
            db.commit()
            async for chunk in pipe.chunks():
                await response.send(chunk)

    await response.eof()


@ticket.websocket("/<id>/wait")
async def wait(request: Request, ws: WebsocketImplProtocol, id: str):
    db = request.ctx.db
    q = request.app.ctx.download_queue
    active = request.app.ctx.active_downloads
    ticket = db.get(Ticket, id)
    if ticket is None:
        raise exception.NotFoundError({"id": "Ticket not found"})

    def _position():
        offset = q.index(id) if id in q else len(q)
        return offset + len(active) - request.app.config.SIMULTANEOURS_DOWNLOADS_LIMIT

    async def send_position(position: int):
        await ws.send(
            json.dumps(
                {"position": position, "available": ticket.is_available},
            ),
        )

    position = _position()
    if position < 0:
        ticket.is_available = True
        db.commit()
    await send_position(position)
    if ticket.is_available:
        log.debug("Ticket %s is already available. Closing connection", id)
        await ws.close(reason="available")
        return

    if id in q:
        log.debug("%s already in queue as position %s: %s", id, q.index(id), q)
        await ws.send(json.dumps({"error": "Already waiting"}))
        log.debug("Closing connection")
        await ws.close(reason="aleready in queue")
        return

    @utils.on_download_started.connect
    @utils.on_download_completed.connect
    async def download_listener(sender: Any, **kwargs: Any):
        position = _position()
        if position < 0:
            ticket.is_available = True
            db.commit()
        await send_position(position)
        if ticket.is_available:
            await ws.close(reason="available")

    q.append(id)
    log.debug("Appended %s to download queue: %s", id, q)

    try:
        await ws.wait_for_connection_lost(timeout=3600)
    except (WebsocketClosed, asyncio.CancelledError):
        q.remove(id)
        log.debug("Removed %s from download queue: %s", id, q)
        raise
