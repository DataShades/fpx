from __future__ import annotations


import jwt

from sanic import Blueprint, request
from webargs_sanic.sanicparser import use_kwargs

from fpx import utils
from fpx.model import Client, Ticket

from .. import schema, exception, pipes

stream = Blueprint("stream", url_prefix="/stream")


@stream.get("/url/<url>")
@use_kwargs(schema.StreamUrl(), location="query")
async def url(request: request.Request, url, client):
    db = request.ctx.db
    client = request.ctx.db.query(Client).filter_by(name=client).one_or_none()
    if not client:
        raise exception.NotFound({"client": "Client not found"})

    try:
        details = jwt.decode(
            url, client.id, algorithms=[request.app.config.JWT_ALGORITHM]
        )
    except jwt.DecodeError as e:
        raise exception.JwtError({"url": {"url": str(e)}}) from e

    if "url" not in details:
        raise exception.JwtError(
            {"url": {"url": "Must be a mapping with `url` key"}}
        )

    ticket = Ticket(type="stream", items=[details["url"]])
    db.add(ticket)
    db.commit()

    db.refresh(ticket)
    response = await request.respond()
    assert response

    async with pipes.Pipe.choose(ticket, request) as pipe:
        response.content_type = details.get("content-type", pipe.content_type())
        filename = pipe.filename()
        response.headers[
            "content-disposition"
        ] = f'attachment; filename="{filename}"'
        response.headers.update(details.get("response_headers", {}))

        with utils.ActiveDownload(request.app.ctx.active_downloads, id):
            db.delete(ticket)
            db.commit()
            async for chunk in pipe.chunks():
                await response.send(chunk)

    await response.eof()
