import secrets
import uuid
import json
from datetime import datetime

from sanic import Sanic
from sqlalchemy import Column, String, create_engine, Text, Boolean, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Session = sessionmaker()
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
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    is_available = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow())

    def __init__(self, type, items):
        self.type = type
        self.items = items

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
    engine = create_engine(app.config.DB_URL)
    Session.configure(bind=engine)
    app.DbSession = Session
