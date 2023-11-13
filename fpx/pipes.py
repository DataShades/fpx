from __future__ import annotations

import abc
import logging
import os
import time
from io import RawIOBase
from typing import AsyncIterable, cast
from zipfile import ZipFile, ZipInfo

import httpx
from typing_extensions import Self

from fpx import exception
from fpx.model import Ticket
from fpx.types import Request

from . import transport

log = logging.getLogger(__name__)


class _Stream(RawIOBase):
    def __init__(self):
        self._buffer = b""
        self._size = 0

    def writable(self):
        return True

    def write(self, b):
        if self.closed:
            msg = "Stream was closed!"
            raise ValueError(msg)
        self._buffer += b
        return len(b)

    def get(self):
        chunk = self._buffer
        self._buffer = b""
        self._size += len(chunk)
        return chunk

    def size(self):
        return self._size


class Pipe(abc.ABC):
    _content_type = "application/octet-stream"
    _filename = "download"

    @classmethod
    def choose(cls, ticket: Ticket, request: Request):
        if ticket.type == "zip":
            pipe = ZipPipe(ticket, request)
        elif ticket.type == "stream":
            if request.app.config.FPX_PIPE_SILLY_STREAM:
                pipe = SillyStreamPipe(ticket, request)
            else:
                pipe = StreamPipe(ticket, request)
        else:
            raise exception.RequestError(
                {"type": f"Unsupported ticket type: {ticket.type}"},
            )
        return pipe

    def __init__(self, ticket: Ticket, request: Request):
        self.ticket = ticket
        self.request = request

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return

    def content_type(self):
        return self._content_type

    def filename(self):
        return self._filename

    @abc.abstractmethod
    async def chunks(self) -> AsyncIterable[bytes]:
        raise NotImplementedError


class ZipPipe(Pipe):
    _content_type = "application/zip"
    _filename = "collection.zip"

    async def __aenter__(self):
        name = self.ticket.options.get("filename")
        if name:
            self._filename = name

        return self

    async def chunks(self) -> AsyncIterable[bytes]:
        stream = _Stream()
        with ZipFile(
            stream,
            mode="w",
        ) as zf:
            tp = transport.choose(self.request)
            async for path, name, content, _resp in tp.stream(
                self.ticket.items,
            ):
                entry = os.path.join(path, name)
                log.debug("Add entry to ZIP archive: %s", entry)
                z_info = ZipInfo(entry, time.gmtime()[:6])
                with zf.open(z_info, mode="w", force_zip64=True) as dest:
                    try:
                        total = 0
                        async for chunk in content:
                            dest.write(chunk)
                            total += len(chunk)
                            log.debug(
                                "+Chunk. %sMB(%sKB) of %s are added to the archive",
                                total // 1024 // 1024,
                                total // 1024,
                                name,
                            )
                            yield stream.get()

                    except (TimeoutError, httpx.TimeoutException):
                        log.exception(
                            "TimeoutError while writing %s. Move to the next file",
                            z_info,
                        )

                    except httpx.ReadError:
                        log.exception(
                            "Read error from file %s. Move to the next file",
                            name,
                        )

                    except Exception:
                        log.exception(
                            "Unexpected error from file %s. Move to the next file",
                            name,
                        )

            zf.comment = b"Written by FPX"
        yield stream.get()


class SillyStreamPipe(Pipe):
    def __init__(self, ticket: Ticket, request: Request):
        super().__init__(ticket, request)
        self._content_type = None
        self._filename = None

    async def __aenter__(self):
        tp = transport.choose(self.request)
        async for _path, name, _content, resp in tp.stream(self.ticket.items):
            self._filename = name
            self._content_type = resp.headers.get("content-type")
            break
        return self

    async def chunks(self) -> AsyncIterable[bytes]:
        tp = transport.choose(self.request)
        async for _path, _name, content, _resp in tp.stream(self.ticket.items):
            async for chunk in content:
                yield chunk


class StreamPipe(Pipe):
    def __init__(self, ticket: Ticket, request: Request):
        super().__init__(ticket, request)
        self._content_type = None
        self._filename = None

    async def __aenter__(self):
        self._gen = self._crawl_file()
        async for name, type_, crawler in self._gen:
            self._filename = name
            self._content_type = type_
            self._content = crawler()
            break
        return self

    async def __aexit__(self, exc_type, exc, tb):
        async for _ in self._gen:
            pass

    async def chunks(self) -> AsyncIterable[bytes]:
        async for chunk in self._content:
            yield cast(bytes, chunk)

    async def _crawl_file(self):
        tp = transport.choose(self.request)
        async for _path, name, content, resp in tp.stream(self.ticket.items):

            async def crawler(content=content):
                async for chunk in content:
                    yield chunk

            yield name, resp.headers.get("content-type"), crawler
