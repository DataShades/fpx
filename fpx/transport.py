from __future__ import annotations

import dataclasses
import enum
import logging
import os
import re
from typing import Any, AsyncIterable, Callable, Coroutine, cast
from urllib.parse import unquote_plus, urlparse

import aiohttp
import httpx

from .exception import ConfigError, TransportError, UrlNotAvailableError
from .types import Request


log = logging.getLogger(__name__)
request_timeout = 24 * 60 * 60
disposition_re = re.compile('filename="(.+)"')

CHUNK_SIZE = 1024**2


class UrlType(enum.Enum):
    Generic = enum.auto()
    AzureBlob = enum.auto()


@dataclasses.dataclass
class ItemDetails:
    url: str
    name: str

    path: str = ""
    headers: dict[str, Any] = dataclasses.field(default_factory=dict)
    url_type = UrlType.Generic

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

        self.url_type = _guess_url_type(self.url)


def choose(request: Request, item: dict[str, Any] | str):
    details = (
        ItemDetails.from_dict(item)
        if isinstance(item, dict)
        else ItemDetails.from_str(item)
    )

    if details.url_type is UrlType.AzureBlob:
        try:
            return AzureBlobTransport(details)
        except ValueError:
            pass

    name = cast(str, request.app.config["FPX_TRANSPORT"])

    if name == "aiohttp":
        return AioHttpTransport(details)

    if name == "httpx":
        return HttpxTransport(details)

    raise ConfigError({"transport": f"Unknown transport: {name}"})


def _name_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = parsed.path.rstrip("/")

    if not name:
        name = parsed.hostname

    if not name:
        name = url

    return os.path.basename(name)


def _guess_url_type(url: str) -> UrlType:
    parsed = urlparse(url)

    if host := parsed.hostname:
        if host.endswith(".blob.core.windows.net"):
            return UrlType.AzureBlob

    return UrlType.Generic


class Transport:
    def __init__(self, details: ItemDetails):
        self.exit_callbacks: list[Callable[[], Coroutine[Any, Any, None]]] = []
        self.details = details

    async def get(
        self, url: str, headers: dict[str, Any], timeout: int
    ) -> tuple[AsyncIterable[bytes], str | None, str]:
        raise NotImplementedError

    async def __aenter__(
        self,
    ) -> tuple[str, str, AsyncIterable[bytes], str | None] | None:
        details = self.details

        try:
            log.debug("Fetch a file from %s", details.url)
            content, content_type, name = await self.get(
                details.url,
                headers=details.headers,
                timeout=request_timeout,
            )

            return (details.path, name, content, content_type)

        except (TransportError, aiohttp.ClientError, httpx.HTTPError):
            log.exception("Failed on %s", details.url)

    async def __aexit__(self, *args: Any):
        for cb in self.exit_callbacks:
            await cb()

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
    async def get(
        self,
        url: str,
        headers: dict[str, Any],
        timeout: int,
    ) -> tuple[AsyncIterable[bytes], str | None, str]:
        session = aiohttp.ClientSession()
        resp = await session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout),
        )
        log.info("Got a %s(%s) response from %s", resp.status, resp.reason, url)

        self.exit_callbacks.append(resp.release)

        if resp.status != 200:
            raise UrlNotAvailableError(resp.status)

        name = self.name_from_resp(resp, self.details.name) or self.details.name
        return self.content_iterator(resp), resp.headers.get("content-type"), name

    def content_iterator(self, resp: aiohttp.ClientResponse):
        return resp.content.iter_chunked(CHUNK_SIZE)


class HttpxTransport(Transport):
    async def get(
        self,
        url: str,
        headers: dict[str, Any],
        timeout: int,
    ) -> tuple[AsyncIterable[bytes], str | None, str]:
        client = httpx.AsyncClient()
        req = client.build_request("GET", url, headers=headers, timeout=timeout)
        resp = await client.send(req, stream=True)
        log.info(
            "Got a %s(%s) response from %s", resp.status_code, resp.reason_phrase, url
        )
        self.exit_callbacks.append(resp.aclose)

        if resp.status_code != 200:
            raise UrlNotAvailableError(resp.status_code)

        name = self.name_from_resp(resp, self.details.name) or self.details.name
        return self.content_iterator(resp), resp.headers.get("content-type"), name

    def content_iterator(self, resp: httpx.Response):
        return resp.aiter_bytes(CHUNK_SIZE)


try:
    from azure.storage.blob.aio import BlobClient
    from azure.core.exceptions import ClientAuthenticationError

    class AzureBlobTransport(Transport):  # type: ignore
        RETRY_ATTEMPTS = 5

        async def get(
            self, url: str, headers: dict[str, Any], timeout: int
        ) -> tuple[AsyncIterable[bytes], str | None, str]:
            blob = BlobClient.from_blob_url(url, max_chunk_get_size=CHUNK_SIZE)

            try:
                props = await blob.get_blob_properties()
            except ClientAuthenticationError:
                raise UrlNotAvailableError(403)

            self.exit_callbacks.append(blob.close)
            return (
                self.content_iterator(blob),
                props["content_settings"]["content_type"],
                os.path.basename(props["name"]),
            )

        async def content_iterator(self, resp: BlobClient) -> AsyncIterable[bytes]:
            offset = 0
            attempt = 0
            while True:
                try:
                    stream = await resp.download_blob(offset)
                    async for chunk in stream.chunks():
                        offset += len(chunk)
                        yield chunk

                except Exception:
                    attempt += 1
                    log.exception(
                        "Error during %s(out of %s) attempt to download %s. Downloaded %s bytes",
                        attempt,
                        self.RETRY_ATTEMPTS,
                        resp.blob_name,
                        offset,
                    )
                    if attempt > self.RETRY_ATTEMPTS:
                        raise UrlNotAvailableError(500)
                    else:
                        continue
                else:
                    break

except ImportError:

    class AzureBlobTransport(Transport):
        def __init__(self, details: ItemDetails):
            raise ValueError
