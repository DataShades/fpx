import fpx.model as model


def test_client(db):
    client = model.Client("test")
    assert client.id is None
    db.add(client)
    db.commit()
    assert client.id is not None
    assert client.name == "test"


def test_ticket(db):
    ticket = model.Ticket(type="url")
    ticket.items = [{"url": "https://google.com"}]

    assert ticket.id is None
    db.add(ticket)
    db.commit()

    assert ticket.id is not None
    assert ticket.items == [{"url": "https://google.com"}]
