import jwt
import pytest


def test_no_client(test_client, url_for):
    _, resp = test_client.get(url_for("stream.url", url="hello"))
    assert resp.status == 422
    assert "client" in resp.json["errors"]["query"]


def test_not_real_client(test_client, url_for):
    _, resp = test_client.get(url_for("stream.url", url="hello", client="test"))
    assert resp.status == 404


def test_invalid_jwt(test_client, url_for, client):
    _, resp = test_client.get(url_for("stream.url", url="hello", client=client.name))
    assert resp.status == 422


def test_valid_jwt_without_url(test_client, url_for, client):
    encoded = jwt.encode(
        {"hello": "world"},
        client.id,
        algorithm=test_client.app.config.JWT_ALGORITHM,
    )
    _, resp = test_client.get(url_for("stream.url", url=encoded, client=client.name))
    assert resp.status == 422


@pytest.mark.usefixtures("all_transports")
def test_valid_jwt(test_client, url_for, client, rmock, faker):
    url = faker.uri()
    body = faker.binary()
    content_type = "application/pdf"

    rmock(url, body=body, headers={"content-type": content_type})
    rmock(url, body=body, headers={"content-type": content_type})

    encoded = jwt.encode(
        {"url": url},
        client.id,
        algorithm=test_client.app.config.JWT_ALGORITHM,
    )
    _, resp = test_client.get(url_for("stream.url", url=encoded, client=client.name))

    assert resp.status == 200
    assert resp.content == body
    assert resp.content_type == content_type
