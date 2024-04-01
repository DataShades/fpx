from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime
from typing import Any, Dict, Iterable

from sqlalchemy import JSON, Text
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    scoped_session,
    sessionmaker,
)

Session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False),
)


class Base(DeclarativeBase):
    type_annotation_map = {Dict[str, Any]: JSON}


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(primary_key=True, default=secrets.token_urlsafe)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"<Client {self.name}({self.id})>"

    def for_json(self, include_id: bool = False) -> dict[str, Any]:
        data = {"name": self.name}
        if include_id:
            data["id"] = self.id

        return data


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    type: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[Dict[str, Any]] = mapped_column(nullable=False, default=dict)
    is_available: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow())

    @property
    def items(self) -> Iterable[str | dict[str, Any]]:
        try:
            return json.loads(self.content)
        except ValueError:
            return []

    @items.setter
    def items(self, value: Iterable[str | dict[str, Any]]):
        self.content = json.dumps(value)

    def for_json(self, include_id: bool = False) -> dict[str, Any]:
        data = {"created": self.created_at.isoformat(), "type": self.type}
        if include_id:
            data["id"] = self.id

        return data
