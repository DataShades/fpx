from __future__ import annotations

import logging
import asyncio
import json
from typing import Any

from sqlalchemy.orm.query import Query
from sanic import Blueprint, response, request
from sanic.server.websockets.impl import WebsocketImplProtocol
from sanic.exceptions import WebsocketClosed

from fpx.model import Ticket
from fpx import utils

from webargs_sanic.sanicparser import use_kwargs
from .. import schema

from . import ticket, stream

log = logging.getLogger(__name__)


def add_routes(app):
    app.blueprint(stream.stream)
    app.blueprint(ticket.ticket)
