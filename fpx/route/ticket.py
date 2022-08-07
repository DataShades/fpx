from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
import aiohttp

from sanic import Blueprint, request, response
from sanic.exceptions import WebsocketClosed
from sanic.server.websockets.impl import WebsocketImplProtocol
from sqlalchemy.orm.query import Query
from webargs_sanic.sanicparser import use_kwargs

from fpx import utils
from fpx.model import Ticket

from .. import schema, exception

log = logging.getLogger(__name__)

ticket = Blueprint("ticket", url_prefix="/ticket")


@ticket.get("/")
@use_kwargs(schema.TicketIndex(), location="query")
async def index(request: request.Request, page: int) -> response.HTTPResponse:
    limit = 10
    base: Query[Ticket] = request.ctx.db.query(Ticket)
    q = base.limit(limit).offset(limit * page - limit)
    return response.json(
        {
            "page": page,
            "count": base.count(),
            "tickets": [t.for_json() for t in q],
        }
    )


@ticket.route("/generate", methods=["POST"], ctx_requires_client=True)
@use_kwargs(schema.TicketGenerate(), location="json")
async def generate(
    request: request.Request, type: str, items: Any, options: dict[str, Any]
) -> response.HTTPResponse:
    ticket = Ticket(type=type, items=items, options=options)
    request.ctx.db.add(ticket)
    request.ctx.db.commit()

    return response.json(ticket.for_json(include_id=True))


@ticket.route("/<id>/download/single")
async def download_single(request: request.Request, id: str) -> response.HTTPResponse:
    db = request.ctx.db
    ticket = db.query(Ticket).get(id)

    if ticket is None:
        raise exception.NotFound({"id": "Ticket not found"})

    if len(ticket.items) != 1:
        raise exception.RequestError({"items": "Not a single-item ticket"})

    async with aiohttp.ClientSession() as session:
        async for fetched_file in utils.fetch_file(ticket.items[0], session):
            _path, name, content, resp = fetched_file

            content_type = resp.content_type

            async def stream_fn(response):
                db.delete(ticket)
                db.commit()
                async for chunk in content.iter_chunked(utils.chunk_size):
                    await response.write(chunk)

            return response.ResponseStream(
                stream_fn,
                content_type=content_type,
                headers={"Content-disposition": f'inline; filename="{name}"'}
            )

        raise exception.NotFound({"items": "File not found"})


@ticket.route("/<id>/download")
async def download(request: request.Request, id: str) -> response.HTTPResponse:
    db = request.ctx.db
    ticket = db.query(Ticket).get(id)

    if ticket is None:
        raise exception.NotFound({"id": "Ticket not found"})

    if not ticket.is_available:
        raise exception.NotAuthorized(
            {"access": "You must wait untill download is available"}
        )

    async def stream_fn(response):
        with utils.ActiveDownload(request.app.ctx.active_downloads, id):
            db.delete(ticket)
            db.commit()
            async for chunk in utils.stream_ticket(ticket):
                await response.write(chunk)

    filename = ticket.options.get("filename", "collection.zip")
    return response.ResponseStream(
        stream_fn,
        headers={"content-disposition": f'attachment; filename="{filename}"'},
        content_type="application/zip",
    )


@ticket.websocket("/<id>/wait")
async def wait(request: request.Request, ws: WebsocketImplProtocol, id: str):
    db = request.ctx.db
    q = request.app.ctx.download_queue
    active = request.app.ctx.active_downloads
    ticket = db.query(Ticket).get(id)
    if ticket is None:
        raise exception.NotFound({"id": "Ticket not found"})

    def _position():
        offset = q.index(id) if id in q else len(q)
        return (
            offset
            + len(active)
            - request.app.config.SIMULTANEOURS_DOWNLOADS_LIMIT
        )

    async def send_position(position):
        await ws.send(
            json.dumps(
                {"position": position, "available": ticket.is_available}
            )
        )

    position = _position()
    if position < 0:
        ticket.is_available = True
        db.commit()
    await send_position(position)
    if ticket.is_available:
        log.debug(f"Ticket {id} is already available. Closing connection")
        await ws.close(reason="available")
        return

    if id in q:
        log.debug(f"{id} already in queue as position {q.index(id)}: {q}")
        await ws.send(json.dumps({"error": "Already waiting"}))
        log.debug("Closing connection")
        await ws.close(reason="aleready in queue")
        return

    @utils.on_download_started.connect
    @utils.on_download_completed.connect
    async def download_listener(sender, **kwargs):
        position = _position()
        if position < 0:
            ticket.is_available = True
            db.commit()
        await send_position(position)
        if ticket.is_available:
            await ws.close(reason="available")

    q.append(id)
    log.debug(f"Appended {id} to download queue: {q}")

    try:
        await ws.wait_for_connection_lost(timeout=3600)
    except (WebsocketClosed, asyncio.CancelledError):
        q.remove(id)
        log.debug(f"Removed {id} from download queue: {q}")
        raise
