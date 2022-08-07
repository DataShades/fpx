from __future__ import annotations

import logging
import os
import re
import time
from asyncio.exceptions import TimeoutError
from io import RawIOBase
from typing import Any
from urllib.parse import unquote_plus
from zipfile import ZipFile, ZipInfo

import aiohttp
from aiohttp.client_exceptions import ClientError
from asyncblink import signal

from fpx.model import Ticket

log = logging.getLogger(__name__)
chunk_size = 1024 * 256
request_timeout = 24 * 60 * 60
on_download_completed = signal("fpx:download-completed")
on_download_started = signal("fpx:download-started")
disposition_re = re.compile('filename="(.+)"')


class Stream(RawIOBase):
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


async def stream_ticket(ticket: Ticket, chunk_size: int = chunk_size):
    stream = Stream()
    with ZipFile(
        stream,
        mode="w",
    ) as zf:
        async for path, name, content, _resp in stream_downloaded_files(
            ticket.items
        ):
            z_info = ZipInfo(os.path.join(path, name), time.gmtime()[:6])
            with zf.open(z_info, mode="w", force_zip64=True) as dest:
                try:
                    total = 0
                    async for chunk in content.iter_chunked(chunk_size):
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


async def stream_downloaded_files(items):
    async with aiohttp.ClientSession() as session:
        for item in items:
            async for result in fetch_file(item, session):
                yield result


async def fetch_file(item, session: aiohttp.ClientSession):
    name = (None,)
    path = ""
    headers = {}
    if isinstance(item, dict):
        url = item["url"]
        path = item.get("path", path)
        name = item.get("name") or os.path.basename(url)
        headers = item.get("headers", headers)
    else:
        url = item
        name = os.path.basename(url.rstrip("/"))
    try:
        simplified_name = os.path.basename(
            unquote_plus(unquote_plus(unquote_plus(name)))
        )
        if simplified_name:
            name = simplified_name
    except Exception:
        log.exception("Cannot simplify name: %s", name)
    try:
        async with session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=request_timeout),
        ) as resp:
            disposition = resp.headers.get("content-disposition")
            if disposition and name not in item:
                match = disposition_re.match(disposition)
                if match:
                    name = match.group(1)
            yield path, name, resp.content, resp
    except ClientError:
        log.exception(f"Failed on {url}")


class ActiveDownload:
    def __init__(self, downloads, id):
        self.id = id
        self.downloads = downloads

    def __enter__(self):
        self.downloads.append(self.id)
        on_download_started.send(self.id, downloads=self.downloads)

    def __exit__(self, type, value, tb):
        self.downloads.remove(self.id)
        on_download_completed.send(self.id, downloads=self.downloads)
