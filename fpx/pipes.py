from __future__ import annotations
import abc
import os
import time
import logging
from typing_extensions import Self

from zipfile import ZipFile, ZipInfo
from typing import AsyncIterable, cast
from io import RawIOBase

from sanic import request

from fpx import exception
from fpx.model import Ticket

from . import utils

log = logging.getLogger(__name__)
CHUNK_SIZE = 1024 * 256


class _Stream(RawIOBase):
    def __init__(self):
        self._buffer = b""
        self._size = 0

    def writable(self):
        return True

    def write(self, b):
        if self.closed:
            raise ValueError("Stream was closed!")
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
    def choose(cls, ticket: Ticket, request: request.Request):
        if ticket.type == "zip":
            pipe = ZipPipe(ticket)
        elif ticket.type == "stream":
            if request.app.config.FPX_PIPE_SILLY_STREAM:
                pipe = SillyStreamPipe(ticket)
            else:
                pipe = StreamPipe(ticket)
        else:
            raise exception.RequestError(
                {"type": f"Unsupported ticket type: {ticket.type}"}
            )
        return pipe

    def __init__(self, ticket: Ticket):
        self.ticket = ticket

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def content_type(self):
        return self._content_type

    def filename(self):
        return self._filename

    @abc.abstractmethod
    async def chunks(self) -> AsyncIterable[bytes]:
        raise NotImplementedError()


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
            async for path, name, content, _resp in utils.stream_downloaded_files(
                self.ticket.items
            ):
                z_info = ZipInfo(os.path.join(path, name), time.gmtime()[:6])
                with zf.open(z_info, mode="w", force_zip64=True) as dest:
                    try:
                        total = 0
                        async for chunk in content.iter_chunked(CHUNK_SIZE):
                            dest.write(chunk)
                            total += len(chunk)
                            log.debug(
                                "+Chunk %sKB / %sMB",
                                total // 1024,
                                total // 1024 // 1024,
                            )
                            yield stream.get()
                    except TimeoutError:
                        log.exception(f"TimeoutError while writing {z_info}")
            zf.comment = b"Written by FPX"
        yield stream.get()


class SillyStreamPipe(Pipe):
    def __init__(self, ticket: Ticket):
        super().__init__(ticket)
        self._content_type = None
        self._filename = None

    async def __aenter__(self):
        async for _path, name, _content, resp in utils.stream_downloaded_files(
            self.ticket.items
        ):
            self._filename = name
            self._content_type = resp.content_type
            break
        return self

    async def chunks(self) -> AsyncIterable[bytes]:
        async for path, name, content, resp in utils.stream_downloaded_files(
            self.ticket.items
        ):

            async for chunk in content.iter_chunked(CHUNK_SIZE):
                yield chunk


class StreamPipe(Pipe):
    def __init__(self, ticket: Ticket):
        super().__init__(ticket)
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
        assert self._content
        async for chunk in self._content:
            yield cast(bytes, chunk)

    async def _crawl_file(self):
        async for path, name, content, resp in utils.stream_downloaded_files(
            self.ticket.items
        ):

            async def crawler():
                async for chunk in content.iter_chunked(CHUNK_SIZE):
                    yield chunk

            yield name, resp.content_type, crawler
