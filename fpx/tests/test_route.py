
import pytest
from fpx import model as m

class TestIndex:
    def test_empty(self, reusable_client):
        _, resp = reusable_client.get("/ticket")
        assert resp.status == 200
        assert resp.json == {"count": 0, "tickets": []}

    def test_non_empty(self, reusable_client, ticket: m.Ticket):
        _, resp = reusable_client.get("/ticket")
        assert resp.json == {"count": 1, "tickets": [{
            "created": ticket.created_at.isoformat(),
            "type": ticket.type
        }]}

    def test_paginated(self, reusable_client, ticket_factory, url_for):
        ticket_factory.create_batch(21)

        _, naive_resp = reusable_client.get(url_for("ticket.index"))
        assert naive_resp.json["count"] == 21
        assert len(naive_resp.json["tickets"]) == 10

        _, resp = reusable_client.get(url_for("ticket.index", page=1))
        assert resp.json == naive_resp.json

        _, resp = reusable_client.get(url_for("ticket.index", page=2))
        assert resp.json["count"] == 21
        assert len(resp.json["tickets"]) == 10

        _, resp = reusable_client.get(url_for("ticket.index", page=3))
        assert resp.json["count"] == 21
        assert len(resp.json["tickets"]) == 1
