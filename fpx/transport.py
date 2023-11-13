from __future__ import annotations

import dataclasses
import logging
import os
import re
from typing import Any, AsyncIterable
from urllib.parse import unquote_plus, urlparse

import aiohttp
import httpx

from .exception import ConfigError, TransportError
from .types import Request

log = logging.getLogger(__name__)
request_timeout = 24 * 60 * 60
disposition_re = re.compile('filename="(.+)"')

CHUNK_SIZE = 1024**2


@dataclasses.dataclass
class ItemDetails:
    url: str
    name: str

    path: str = ""
    headers: dict[str, Any] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_dict(cls, item: dict[str, Any]):
        url = item["url"]

        details = cls(
            url,
            item.get("name") or _name_from_url(url),
        )

        if path := item.get("path"):
            details.path = path

        if headers := item.get("headers"):
            details.headers = headers

        return details

    @classmethod
    def from_str(cls, url: str):
        return cls(
            url,
            _name_from_url(url),
        )

    def __post_init__(self):
        try:
            self.name = os.path.basename(
                unquote_plus(unquote_plus(unquote_plus(self.name))),
            )
        except Exception:
            log.exception("Cannot simplify name: %s", self.name)


def choose(request: Request):
    name: str = request.app.config["FPX_TRANSPORT"]
    if name == "aiohttp":
        return AioHttpTransport()

    if name == "httpx":
        return HttpxTransport()

    raise ConfigError({"transport": f"Unknown transport: {name}"})


def _name_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = parsed.path.rstrip("/")

    if not name:
        name = parsed.hostname

    if not name:
        name = url

    return os.path.basename(name)


class Transport:
    async def get(
        self,
        url: str,
        headers: dict[str, Any],
        timeout: int,
    ) -> AsyncIterable[tuple[Any, int, str]]:
        raise NotImplementedError

    async def stream(self, items: list[Any]):
        for item in items:
            async for result in self.fetch_item(item):
                yield result

    async def fetch_item(
        self,
        item: str | dict[str, Any],
    ) -> AsyncIterable[tuple[str, str, AsyncIterable[Any], Any]]:
        if isinstance(item, dict):
            details = ItemDetails.from_dict(item)
        else:
            details = ItemDetails.from_str(item)

        try:
            log.debug("Fetch a file from %s", details.url)
            async for resp, status, reason in self.get(
                details.url,
                headers=details.headers,
                timeout=request_timeout,
            ):
                log.info("Got a %s(%s) response from %s", status, reason, details.url)
                name = self.name_from_resp(resp, details.name) or details.name
                yield details.path, name, self.content_iterator(resp), resp

        except (TransportError, aiohttp.ClientError, httpx.HTTPError):
            log.exception("Failed on %s", details.url)

    def name_from_resp(self, resp: Any, default_name: str) -> str | None:
        disposition = resp.headers.get("content-disposition")
        if disposition and not default_name:
            match = disposition_re.match(disposition)
            if match:
                return match.group(1)
            return None

        return None

    def unquote_name(self, name: str) -> str:
        try:
            return os.path.basename(
                unquote_plus(unquote_plus(unquote_plus(name))),
            )
        except Exception:
            log.exception("Cannot simplify name: %s", name)
            return name

    def content_iterator(self, resp: Any) -> AsyncIterable[bytes]:
        raise NotImplementedError


class AioHttpTransport(Transport):
    async def stream(self, items: list[Any]):
        async with aiohttp.ClientSession() as session:
            self.session = session
            async for item in super().stream(items):
                yield item

    async def get(
        self,
        url: str,
        headers: dict[str, Any],
        timeout: int,
    ) -> AsyncIterable[tuple[aiohttp.ClientResponse, int, str]]:
        async with self.session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            yield resp, resp.status, resp.reason or ""

    def content_iterator(self, resp: aiohttp.ClientResponse):
        return resp.content.iter_chunked(CHUNK_SIZE)


class HttpxTransport(Transport):
    async def stream(self, items: list[Any]):
        async with httpx.AsyncClient() as session:
            self.session = session
            async for item in super().stream(items):
                yield item

    async def get(
        self,
        url: str,
        headers: dict[str, Any],
        timeout: int,
    ) -> AsyncIterable[tuple[httpx.Response, int, str]]:
        async with self.session.stream(
            "GET",
            url,
            headers=headers,
            timeout=timeout,
        ) as resp:
            yield resp, resp.status_code, resp.reason_phrase

    def content_iterator(self, resp: httpx.Response):
        return resp.aiter_bytes(CHUNK_SIZE)
