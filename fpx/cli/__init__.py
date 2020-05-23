import click

from . import server, db, client, ticket
from fpx.app import make_app


@click.group(no_args_is_help=True)
@click.pass_context
def fpx(ctx):
    ctx.obj = make_app()


fpx.add_command(server.server)
fpx.add_command(db.db)
fpx.add_command(client.client)
fpx.add_command(ticket.ticket)
