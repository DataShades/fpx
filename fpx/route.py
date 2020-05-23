import logging
import asyncio
import json

from collections import deque
from sanic import Blueprint, response, request, exceptions, websocket

from fpx.model import Client, Ticket
from fpx import utils, decorator

log = logging.getLogger(__name__)


def add_routes(app):
    app.blueprint(ticket)


ticket = Blueprint("ticket", url_prefix="/ticket")


@ticket.route("/generate", methods=["POST"])
@decorator.client_only
def generate(request: request.Request):
    required_fields = ["type", "items"]
    if not request.json:
        return response.json({"error": f"requires json payload"}, 409)

    for field in required_fields:
        if field not in request.json:
            return response.json({"error": f'missing "{field}" field'}, 409)
    ticket = Ticket(request.json["type"], request.json["items"])
    request.ctx.db.add(ticket)
    request.ctx.db.commit()
    return response.json(
        dict(
            id=ticket.id,
            items=ticket.items,
            type=ticket.type,
            download_url=request.url_for("ticket.download", id=ticket.id),
        )
    )


@ticket.route("/<id>/download")
async def download(request: request.Request, id: str):
    db = request.ctx.db
    ticket = db.query(Ticket).get(id)
    if ticket is None:
        raise exceptions.NotFound("Ticket not found")
    if not ticket.is_available:
        raise exceptions.abort(
            403, "You must wait untill download is available"
        )

    async def stream_fn(response):
        with utils.ActiveDownload(request.app.active_downloads, id):
            async for chunk in utils.stream_ticket(ticket):
                await response.write(chunk)
        db.delete(ticket)
        db.commit()

    return response.stream(stream_fn, content_type="application/zip")


@ticket.websocket("/<id>/wait")
async def wait(
    request: request.Request, ws: websocket.WebSocketCommonProtocol, id: str
):
    db = request.ctx.db
    q = request.app.download_queue
    active = request.app.active_downloads
    ticket = db.query(Ticket).get(id)
    if ticket is None:
        raise exceptions.NotFound("Ticket not found")

    def _position():
        return (
            q.index(id) + len(active)
            - request.app.config.SIMULTANEOURS_DOWNLOADS_LIMIT
        )

    async def send_position(position):
        await ws.send(
            json.dumps(
                {"position": position, "available": ticket.is_available}
            )
        )

    position = _position()
    if position <= 0:
        ticket.is_available = True
        db.commit()
    await send_position(position)
    if ticket.is_available:
        log.debug(f"Ticket {id} is already available. Closing connection")
        await ws.close()
        return

    if id in q:
        log.debug(f"{id} already in queue as position {q.index(id)}: {q}")
        await ws.send(json.dumps({"error": "Already waiting"}))
        log.debug("Closing connection")
        await ws.close()
        return

    @utils.on_download_started.connect
    @utils.on_download_completed.connect
    async def download_listener(sender, **kwargs):
        position = _position()
        if position <= 0:
            ticket.is_available = True
            db.commit()
        await send_position(position)
        if ticket.is_available:
            await ws.close()

    q.append(id)
    log.debug(f"Appended {id} to download queue: {q}")

    try:
        await ws.wait_closed()
    except (websocket.ConnectionClosed, asyncio.CancelledError):
        q.remove(id)
        log.debug(f"Removed {id} from download queue: {q}")
        raise
