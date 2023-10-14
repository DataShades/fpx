from __future__ import annotations

import logging

from . import stream, ticket

log = logging.getLogger(__name__)


def add_routes(app):
    app.blueprint(stream.stream)
    app.blueprint(ticket.ticket)
