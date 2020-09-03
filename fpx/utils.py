import logging
import re
import os
from asyncblink import signal
from zipfile import ZipFile, ZipInfo
import time
from io import RawIOBase
import aiohttp
from aiohttp.client_exceptions import ClientError
from sanic.response import StreamingHTTPResponse

from fpx.model import Ticket

log = logging.getLogger(__name__)
chunk_size = 1024 * 64
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
    with ZipFile(stream, mode="w",) as zf:
        async for path, name, content in stream_downloaded_files(ticket.items):
            z_info = ZipInfo(os.path.join(path, name), time.gmtime()[:6])
            with zf.open(z_info, mode="w") as dest:
                async for chunk in content.iter_chunked(chunk_size):
                    dest.write(chunk)
                    yield stream.get()
        zf.comment = b"Written by FPX"
    yield stream.get()


async def stream_downloaded_files(items):
    async with aiohttp.ClientSession() as session:
        for item in items:
            name = None,
            path = ''
            headers = {}
            if isinstance(item, dict):
                url = item['url']
                path = item.get('path', path)
                name = item.get('name') or os.path.basename(url)
                headers = item.get('headers', headers)
            else:
                url = item
                name = os.path.basename(url)
            try:
                async with session.get(url, headers=headers) as resp:
                    disposition = resp.headers.get('content-disposition')
                    if disposition and name not in item:
                        match = disposition_re.match(disposition)
                        if match:
                            name = match.group(1)
                    yield path, name, resp.content
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
