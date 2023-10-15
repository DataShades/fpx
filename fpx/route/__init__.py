from __future__ import annotations

from fpx.types import App

from . import stream, ticket


def add_routes(app: App):
    app.blueprint(stream.stream)
    app.blueprint(ticket.ticket)
