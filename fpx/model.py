from __future__ import annotations

import secrets
from typing import Any
import uuid
import json
from datetime import datetime

from sanic import Sanic
from sqlalchemy import (
    Column,
    String,
    create_engine,
    Text,
    Boolean,
    DateTime,
    JSON,
    orm,
)

from sqlalchemy.ext.declarative import declarative_base

Session = orm.sessionmaker()
scoped_session = orm.scoped_session(Session)

Base = declarative_base()


class Client(Base):
    __tablename__ = "clients"
    id = Column(String, primary_key=True, default=secrets.token_urlsafe)
    name = Column(String, unique=True, nullable=False)

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"<Client {self.name}({self.id})>"


class Ticket(Base):
    __tablename__ = "tickets"
    id: str = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
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


def make_db_session(app: Sanic):
    engine = create_engine(app.config.DB_URL, **app.config.DB_EXTRAS)
    Session.configure(bind=engine)
    app.ctx.DbSession = Session
