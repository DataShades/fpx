from __future__ import annotations

import logging
import os
import re
from urllib.parse import unquote_plus

import aiohttp
from aiohttp.client_exceptions import ClientError
from asyncblink import signal

log = logging.getLogger(__name__)
request_timeout = 24 * 60 * 60
on_download_completed = signal("fpx:download-completed")
on_download_started = signal("fpx:download-started")
disposition_re = re.compile('filename="(.+)"')


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
