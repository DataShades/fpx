import logging
import asyncio
import json
import base64
from typing import Union

from sanic import Blueprint, response, request
from sanic.server.websockets.impl import WebsocketImplProtocol
from sanic.exceptions import WebsocketClosed

from fpx.model import Ticket
from fpx import utils, decorator

log = logging.getLogger(__name__)


def add_routes(app):
    app.blueprint(ticket)


ticket = Blueprint("ticket", url_prefix="/ticket")


@ticket.route("/")
async def index(request: request.Request):
    return response.text("Hello, world.")
    q = request.ctx.db.query(Ticket)
    return response.json({"count": q.count(), "tickets": [
        {"created": t.created_at.isoformat(), "type": t.type}
        for t in q
    ]})

@ticket.route("/generate", methods=["POST"])
@decorator.client_only
def generate(request: request.Request):
    required_fields = ["type", "items"]
    if not request.json:
        return response.json({"error": f"requires json payload"}, 409)

    for field in required_fields:
        if field not in request.json:
            return response.json({"error": f'missing "{field}" field'}, 409)
    items: Union[str, bytes] = request.json["items"]
    try:
        if isinstance(items, str):
            items = items.encode("utf8")
        items = json.loads(base64.decodebytes(items))
    except ValueError:
        return response.json(
            {"error": "Must be a base64-decoded JSON-string"}, 409
        )

    try:
        options = json.loads(
            base64.decodebytes(bytes(request.json.get("options"), "utf8"))
        )
    except (ValueError, TypeError):
        options = {}

    ticket = Ticket(type=request.json["type"], items=items, options=options)

    request.ctx.db.add(ticket)
    request.ctx.db.commit()
    return response.json(
        dict(
            id=ticket.id,
            items=ticket.items,
            type=ticket.type,
        )
    )


@ticket.route("/<id>/download")
async def download(request: request.Request, id: str):
    db = request.ctx.db
    ticket = db.query(Ticket).get(id)
    if ticket is None:
        return response.json({"error": "Ticket not found"}, 404)
    if not ticket.is_available:
        return response.json(
            {"error": "You must wait untill download is available"}, 403
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
async def wait(
    request: request.Request, ws: WebsocketImplProtocol, id: str
):
    db = request.ctx.db
    q = request.app.ctx.download_queue
    active = request.app.ctx.active_downloads
    ticket = db.query(Ticket).get(id)
    if ticket is None:
        return response.json({"error": "Ticket not found"}, 404)

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
