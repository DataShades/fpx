import base64
import json
import os
from io import BytesIO
from zipfile import ZipFile

import pytest

from fpx import model as m


class TestIndex:
    def test_empty(self, rc, url_for):
        _, resp = rc.get(url_for("ticket.index"))
        assert resp.status == 200
        assert resp.json == {"page": 1, "count": 0, "tickets": []}

    def test_non_empty(self, rc, ticket: m.Ticket, url_for):
        _, resp = rc.get(url_for("ticket.index"))
        assert resp.json == {
            "page": 1,
            "count": 1,
            "tickets": [
                {"created": ticket.created_at.isoformat(), "type": ticket.type}
            ],
        }

    def test_paginated(self, rc, ticket_factory, url_for):
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
    def test_anonymous(self, rc, url_for):
        _, resp = rc.post(url_for("ticket.generate"))
        assert resp.status == 401

    def test_missing(self, rc, url_for, client):
        _, resp = rc.post(
            url_for("ticket.generate"), headers={"authorize": client.id}
        )
        assert resp.status == 422
        assert set(resp.json["errors"]["json"].keys()) == {"type", "items"}

    def test_items_not_a_string_or_expected(self, rc, url_for, client):
        payload = {"type": "url", "items": 123}
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 422
        assert set(resp.json["errors"]["json"].keys()) == {"items"}

    def test_items_not_a_base64(self, rc, url_for, client):
        payload = {"type": "url", "items": "hello world"}
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 422
        assert set(resp.json["errors"]["json"].keys()) == {"items"}

    def test_items_not_a_json(self, rc, url_for, client):
        payload = {
            "type": "url",
            "items": base64.encodebytes(b"hello world").decode("utf8"),
        }
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 422
        assert set(resp.json["errors"]["json"].keys()) == {"items"}

    def test_valid_encoded_payload(self, rc, url_for, client, db):
        payload = {
            "type": "url",
            "items": base64.encodebytes(b'["http://google.com"]').decode(
                "utf8"
            ),
        }
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 200

        ticket: m.Ticket = (
            db.query(m.Ticket).filter_by(id=resp.json["id"]).one()
        )
        assert ticket.items == ["http://google.com"]
        assert ticket.type == payload["type"]

    def test_stream_ticket_with_one_item(self, rc, url_for, client, db):
        payload = {"type": "stream", "items": ["http://google.com"]}
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 200

    def test_stream_ticket_with_zero_items(self, rc, url_for, client, db):
        payload = {"type": "stream", "items": []}
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 422
        assert set(resp.json["errors"]["json"].keys()) == {"type"}

    def test_stream_ticket_with_multiple_items(self, rc, url_for, client, db):
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

    def test_valid_raw_payload(self, rc, url_for, client, db):
        payload = {"type": "url", "items": ["http://google.com"]}
        _, resp = rc.post(
            url_for("ticket.generate"),
            headers={"authorize": client.id},
            json=payload,
        )
        assert resp.status == 200

        ticket: m.Ticket = (
            db.query(m.Ticket).filter_by(id=resp.json["id"]).one()
        )
        assert ticket.items == payload["items"]
        assert ticket.type == payload["type"]


class TestDownload:
    def test_non_existing(self, rc, url_for):
        _, resp = rc.get(url_for("ticket.download", id="not-real"))
        assert resp.status == 404

    def test_not_available(self, rc, url_for, ticket):
        _, resp = rc.get(url_for("ticket.download", id=ticket.id))
        assert resp.status == 403

    @pytest.mark.parametrize("num", [1, 2, 5])
    def test_download(self, num, rc, url_for, ticket_factory, faker, rmock):
        urls = [faker.uri() for _ in range(num)]
        for url in urls:
            rmock.get(url, body=f"hello world, {url}")

        ticket = ticket_factory(content=json.dumps(urls), is_available=True)
        _, resp = rc.get(url_for("ticket.download", id=ticket.id))

        assert resp.status == 200
        z = ZipFile(BytesIO(resp.content))
        assert z.comment == b"Written by FPX"
        assert len(z.filelist) == len(urls)
        for url in urls:
            name = os.path.basename(url.rstrip("/"))
            assert z.read(name) == f"hello world, {url}".encode("utf8")

    def test_download_single(self, rc, url_for, ticket_factory, faker, rmock):
        url = faker.uri()
        rmock.get(url, body=f"hello world, {url}")

        ticket = ticket_factory(content=json.dumps([url]), is_available=True)
        _, resp = rc.get(url_for("ticket.download_single", id=ticket.id))

        assert resp.status == 200
        assert resp.content == f"hello world, {url}".encode("utf8")
