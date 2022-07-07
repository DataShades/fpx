

import pytest

def test_index(app):
    _req, resp = app.test_client.get("/ticket")
    assert resp.status == 200
    assert resp.json == {"count": 0, "tickets": []}


def test_index(app, ticket_factory):
    _req, resp = app.test_client.get("/ticket")
    assert resp.status == 200
    assert resp.json == {"count": 0, "tickets": []}

    ticket_factory()
