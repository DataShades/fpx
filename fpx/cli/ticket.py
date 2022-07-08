from typing import Optional

import click
from sanic import Sanic

from fpx.model import Ticket


@click.group()
def ticket():
    pass


@ticket.command()
@click.pass_obj
def list(app: Sanic):
    for ticket in app.ctx.db_session().query(Ticket):
        click.echo(f"{ticket.id}({ticket.created_at}):")
        for item in ticket.items:
            click.echo(f"\t{item}")
        click.echo()


@ticket.command()
@click.pass_obj
@click.option("--all", is_flag=True)
@click.argument("id", required=False)
def drop(app: Sanic, all: bool, id: Optional[str] = None):
    sess = app.ctx.db_session()
    q = sess.query(Ticket)
    if id:
        q.filter_by(id=id).delete()
    elif all:
        q.delete()
    click.secho("Done", fg="green")
    sess.commit()
