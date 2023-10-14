from __future__ import annotations

import logging

from asyncblink import signal

log = logging.getLogger(__name__)

on_download_completed = signal("fpx:download-completed")
on_download_started = signal("fpx:download-started")


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
