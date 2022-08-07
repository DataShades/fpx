import pytest
import jwt


def test_no_client(rc, url_for):
    _, resp = rc.get(url_for("stream.url", url="hello"))
    assert resp.status == 422
    assert "client" in resp.json["errors"]["query"]


def test_not_real_client(rc, url_for):
    _, resp = rc.get(url_for("stream.url", url="hello", client="test"))
    assert resp.status == 404


def test_invalid_jwt(rc, url_for, client):
    _, resp = rc.get(url_for("stream.url", url="hello", client=client.name))
    assert resp.status == 422


def test_valid_jwt_without_url(rc, url_for, client):
    encoded = jwt.encode(
        {"hello": "world"}, client.id, algorithm=rc.app.config.JWT_ALGORITHM
    )
    _, resp = rc.get(url_for("stream.url", url=encoded, client=client.name))
    assert resp.status == 422


def test_valid_jwt(rc, url_for, client, rmock, faker):
    url = faker.uri()
    body = faker.binary()
    content_type = "application/pdf"

    rmock.get(url, body=body, headers={"content-type": content_type})

    encoded = jwt.encode(
        {"url": url}, client.id, algorithm=rc.app.config.JWT_ALGORITHM
    )
    _, resp = rc.get(url_for("stream.url", url=encoded, client=client.name))

    assert resp.status == 200
    assert resp.content == body
    assert resp.content_type == content_type
