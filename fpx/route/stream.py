from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import jwt

from sanic import Blueprint, request, response
from sanic.exceptions import WebsocketClosed
from sanic.server.websockets.impl import WebsocketImplProtocol
from sqlalchemy.orm.query import Query
from webargs_sanic.sanicparser import use_kwargs

from fpx import utils
from fpx.model import Client

from .. import schema, exception

stream = Blueprint("stream", url_prefix="/stream")


@stream.get("/url/<url>")
@use_kwargs(schema.StreamUrl(), location="query")
async def url(request: request.Request, url, client):
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

    async for path, name, content, _resp in utils.stream_downloaded_files(
        [details]
    ):
        content_type = details.get("content-type", _resp.content_type)

        async def stream_fn(response):
            async for chunk in content.iter_chunked(utils.chunk_size):
                await response.write(chunk)

        return response.ResponseStream(
            stream_fn,
            headers=details.get("response_headers", {}),
            content_type=content_type,
        )
