from fpx import model


def test_client(db):
    """Client can be saved to DB."""
    client = model.Client("test")
    assert client.id is None

    db.add(client)
    db.commit()

    assert client.id is not None
    assert client.name == "test"


def test_client_factory(client):
    """Factory produces client with ID."""

    assert client.id


def test_ticket(db):
    """Ticket can be saved to DB."""
    ticket = model.Ticket(type="url")
    ticket.items = [{"url": "https://google.com"}]
    assert ticket.id is None

    db.add(ticket)
    db.commit()

    assert ticket.id is not None
    assert ticket.items == [{"url": "https://google.com"}]


def test_ticket_factory(ticket):
    """Factory produces ticket with ID."""
    assert ticket.id
