import click
from sanic import Sanic

from fpx.model import Client


@click.group()
def client():
    pass


@client.command()
@click.pass_obj
@click.argument("name")
def add(app: Sanic, name: str):
    sess = app.ctx.db_session()
    client = Client(name)
    sess.add(client)
    sess.commit()
    click.secho(f"Client created: {client.name} - {client.id}", fg="green")


@client.command()
@click.pass_obj
@click.argument("name")
def drop(app: Sanic, name: str):
    sess = app.ctx.db_session()
    sess.query(Client).filter_by(name=name).delete()
    sess.commit()
    click.secho(f"Client removed", fg="green")


@client.command()
@click.pass_obj
@click.argument("name")
def regenerate(app: Sanic, name: str):
    sess = app.ctx.db_session()
    client = sess.query(Client).filter_by(name=name).first()
    sess.delete(client)
    sess.commit()

    new_client = Client(client.name)
    sess.add(new_client)
    sess.commit()
    click.secho(
        f"Client updated: {new_client.name} - {new_client.id}", fg="green"
    )


@client.command()
@click.pass_obj
def list(app: Sanic):
    sess = app.ctx.db_session()
    click.echo("Clients:")
    for client in sess.query(Client):
        click.echo(f"\t{client}")
