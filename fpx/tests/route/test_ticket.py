import base64
import json
import os
from io import BytesIO
from typing import Callable
from zipfile import ZipFile
from sanic_testing.reusable import ReusableClient

import pytest

from fpx import model as m

UrlFor = Callable[..., str]


class TestIndex:
    def test_empty(self, rc: ReusableClient, url_for: UrlFor):
        _, resp = rc.get(url_for("ticket.index"))
        assert resp.status == 200
        assert resp.json == {"page": 1, "count": 0, "tickets": []}

    def test_non_empty(self, rc: ReusableClient, ticket: m.Ticket, url_for: UrlFor):
        _, resp = rc.get(url_for("ticket.index"))
        assert resp.json == {
            "page": 1,
            "count": 1,
            "tickets": [
                {"created": ticket.created_at.isoformat(), "type": ticket.type},
            ],
        }

    def test_paginated(self, rc: ReusableClient, ticket_factory, url_for: UrlFor):
        ticket_factory.create_batch(21)

        _, naive_resp = rc.get(url_for("ticket.index"))
        assert naive_resp.json["count"] == 21
        assert len(naive_resp.json["tickets"]) == 10

        _, resp = rc.get(url_for("ticket.index", page=1))
        assert resp.json == naive_resp.json

        _, resp = rc.get(url_for("ticket.index", page=2))
        assert resp.json["count"] == 21
        assert len(resp.json["tickets"]) == 10

        _, resp = rc.get(url_for("ticket.index", page=3))
        assert resp.json["count"] == 21
        assert len(resp.json["tickets"]) == 1


class TestGenerate:
    def test_anonymous(self, rc: ReusableClient, url_for: UrlFor):
        _, resp = rc.post(url_for("ticket.generate"))
        assert resp.status == 401

    def test_missing(self, rc: ReusableClient, url_for: UrlFor, client):
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
        )
        assert resp.status == 422
        assert set(resp.json["errors"]["json"].keys()) == {"items"}

    def test_items_not_a_string_or_expected(
        self, rc: ReusableClient, url_for: UrlFor, client
    ):
        payload = {"type": "zip", "items": 123}
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 422
        assert set(resp.json["errors"]["json"].keys()) == {"items"}

    def test_items_not_a_base64(self, rc: ReusableClient, url_for: UrlFor, client):
        payload = {"type": "zip", "items": "hello world"}
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 422
        assert set(resp.json["errors"]["json"].keys()) == {"items"}

    def test_items_not_a_json(self, rc: ReusableClient, url_for: UrlFor, client):
        payload = {
            "type": "zip",
            "items": base64.encodebytes(b"hello world").decode("utf8"),
        }
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 422
        assert set(resp.json["errors"]["json"].keys()) == {"items"}

    def test_valid_encoded_payload(
        self, rc: ReusableClient, url_for: UrlFor, client, db
    ):
        payload = {
            "type": "zip",
            "items": base64.encodebytes(b'["http://google.com"]').decode(
                "utf8",
            ),
        }
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 200

        ticket: m.Ticket = db.query(m.Ticket).filter_by(id=resp.json["id"]).one()
        assert ticket.items == ["http://google.com"]
        assert ticket.type == payload["type"]

    def test_stream_ticket_with_one_item(
        self, rc: ReusableClient, url_for: UrlFor, client, db
    ):
        payload = {"type": "stream", "items": ["http://google.com"]}
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 200

    def test_stream_ticket_with_zero_items(
        self, rc: ReusableClient, url_for: UrlFor, client, db
    ):
        payload = {"type": "stream", "items": []}
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 422
        assert set(resp.json["errors"]["json"].keys()) == {"type"}

    def test_stream_ticket_with_multiple_items(
        self, rc: ReusableClient, url_for: UrlFor, client, db
    ):
        payload = {
            "type": "stream",
            "items": ["http://google.com", "http://not-a-google.com"],
        }
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 422
        assert set(resp.json["errors"]["json"].keys()) == {"type"}

    def test_valid_raw_payload(self, rc: ReusableClient, url_for: UrlFor, client, db):
        payload = {"type": "zip", "items": ["http://google.com"]}
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 200

        ticket: m.Ticket = db.query(m.Ticket).filter_by(id=resp.json["id"]).one()
        assert ticket.items == payload["items"]
        assert ticket.type == payload["type"]


@pytest.mark.usefixtures("all_transports")
class TestDownload:
    def test_non_existing(self, rc: ReusableClient, url_for: UrlFor):
        _, resp = rc.get(url_for("ticket.download", id="not-real"))
        assert resp.status == 404

    def test_not_available(self, rc: ReusableClient, url_for: UrlFor, ticket):
        _, resp = rc.get(url_for("ticket.download", id=ticket.id))
        assert resp.status == 403

    @pytest.mark.parametrize("num", [1, 2, 5])
    def test_download(
        self, num, rc: ReusableClient, url_for: UrlFor, ticket_factory, faker, rmock
    ):
        urls = [faker.uri() for _ in range(num)]
        for url in urls:
            rmock(url=url, body=f"hello world, {url}")

        ticket = ticket_factory(content=json.dumps(urls), is_available=True)
        _, resp = rc.get(url_for("ticket.download", id=ticket.id))

        assert resp.status == 200
        z = ZipFile(BytesIO(resp.content))
        assert z.comment == b"Written by FPX"
        assert len(z.filelist) == len(urls)
        for url in urls:
            name = os.path.basename(url.rstrip("/"))
            assert z.read(name) == f"hello world, {url}".encode()

    def test_download_stream(
        self, rc: ReusableClient, url_for: UrlFor, ticket_factory, faker, rmock
    ):
        url = faker.uri()
        rmock(url, body=f"hello world, {url}")
        rmock(url, body=f"hello world, {url}")

        ticket = ticket_factory(
            type="stream",
            content=json.dumps([url]),
            is_available=True,
        )
        _, resp = rc.get(url_for("ticket.download", id=ticket.id))

        assert resp.status == 200
        assert resp.content == f"hello world, {url}".encode()

    def test_download_huge_stream(
        self, rc: ReusableClient, url_for: UrlFor, ticket_factory, faker, rmock
    ):
        size = 1024 * 1024 * 10
        url = faker.uri()
        rmock(url, body="0" * size)
        rmock(url, body="0" * size)

        ticket = ticket_factory(
            type="stream",
            content=json.dumps([url]),
            is_available=True,
        )
        _, resp = rc.get(url_for("ticket.download", id=ticket.id))

        assert resp.status == 200
        assert len(resp.content) == size
