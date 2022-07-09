from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from sanic import Blueprint, request, response
from sanic.exceptions import WebsocketClosed
from sanic.server.websockets.impl import WebsocketImplProtocol
from sqlalchemy.orm.query import Query
from webargs_sanic.sanicparser import use_kwargs

from fpx import utils
from fpx.model import Ticket

from .. import schema
from . import stream, ticket

log = logging.getLogger(__name__)


def add_routes(app):
    app.blueprint(stream.stream)
    app.blueprint(ticket.ticket)
