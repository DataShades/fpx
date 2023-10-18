"""Application context.

This module defines object available as `request.app.ctx` during HTTP requests.

"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from sqlalchemy.orm import Session as AlchemySession
from sqlalchemy.orm.scoping import ScopedSession

from .model import Client, Session


@dataclass
class Context:
    download_queue: deque[str] = field(default_factory=deque)
    active_downloads: list[str] = field(default_factory=list)
    sessionmaker: ScopedSession[AlchemySession] = Session
    client: Client | None = None
    db: AlchemySession = None  # type: ignore

    def db_session(self):
        return self.sessionmaker()
