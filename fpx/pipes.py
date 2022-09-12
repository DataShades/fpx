from __future__ import annotations
import abc
import os
import time
import logging

from zipfile import ZipFile, ZipInfo
from typing import AsyncIterable, cast
from io import RawIOBase

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
    async def choose(cls, ticket: Ticket):
        if ticket.type == "zip":
            pipe = ZipPipe(ticket)
        elif ticket.type == "stream":
            pipe = StreamPipe(ticket)
        else:
            raise exception.RequestError(
                {"type": f"Unsupported ticket type: {ticket.type}"}
            )

        await pipe.prepare()
        return pipe

    def __init__(self, ticket: Ticket):
        self.ticket = ticket

    async def prepare(self):
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

    async def prepare(self):
        name = self.ticket.options.get("filename")
        if name:
            self._filename = name

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


class StreamPipe(Pipe):
    def __init__(self, ticket: Ticket):
        super().__init__(ticket)
        self._content_type = None
        self._filename = None

    async def prepare(self):
        name, type_, content = await self._crawl_file()
        self._filename = name
        self._content_type = type_
        self._content = content

    async def chunks(self) -> AsyncIterable[bytes]:
        assert self._content
        async for chunk in self._content():
            yield cast(bytes, chunk)

    async def _crawl_file(self):
        async for path, name, content, resp in utils.stream_downloaded_files(
            self.ticket.items
        ):

            async def crawler():
                async for chunk in content.iter_chunked(CHUNK_SIZE):
                    yield chunk

            return name, resp.content_type, crawler

        raise exception.RequestError({"items": "Cannot download a file"})
