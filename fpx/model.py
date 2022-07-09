from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text, orm
from sqlalchemy.ext.declarative import declarative_base

Session = orm.scoped_session(
    orm.sessionmaker(autocommit=False, autoflush=False)
)

Base = declarative_base()


class Client(Base):
    __tablename__ = "clients"
    id: str = Column(String, primary_key=True, default=secrets.token_urlsafe)
    name: str = Column(String, unique=True, nullable=False)

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
    id: str = Column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    type: str = Column(String, nullable=False)
    content: str = Column(Text, nullable=False)
    options: dict[str, Any] = Column(JSON, nullable=False, default=dict)
    is_available: bool = Column(Boolean, default=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow())

    @property
    def items(self):
        try:
            return json.loads(self.content)
        except ValueError:
            return []

    @items.setter
    def items(self, value):
        self.content = json.dumps(value)

    def for_json(self, include_id: bool = False) -> dict[str, Any]:
        data = {"created": self.created_at.isoformat(), "type": self.type}
        if include_id:
            data["id"] = self.id

        return data
