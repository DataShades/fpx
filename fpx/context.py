from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from sqlalchemy.orm.scoping import ScopedSession

from .model import Session

__all__ = ["Context"]


@dataclass
class Context:
    download_queue: deque[str] = field(default_factory=deque)
    active_downloads: list[str] = field(default_factory=list)
    sessionmaker: ScopedSession = Session

    def db_session(self):
        return self.sessionmaker()
