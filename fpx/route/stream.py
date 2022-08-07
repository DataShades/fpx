from __future__ import annotations

import aiohttp

import jwt

from sanic import Blueprint, request, response
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

    async with aiohttp.ClientSession() as session:
        async for fetched_file in utils.fetch_file(details, session):
            _path, _name, content, resp = fetched_file
            content_type = details.get("content-type", resp.content_type)

            async def stream_fn(response):
                async for chunk in content.iter_chunked(utils.chunk_size):
                    await response.write(chunk)

            return response.ResponseStream(
                stream_fn,
                headers=details.get("response_headers", {}),
                content_type=content_type,
            )

        raise exception.NotFound({"items": "File not found"})
