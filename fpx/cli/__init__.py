import click

from fpx.app import loader

from . import client, db, server, ticket


@click.group(no_args_is_help=True)
@click.pass_context
def fpx(ctx: click.Context):
    """FPX CLI"""
    ctx.obj = loader.load()


fpx.add_command(server.server)
fpx.add_command(db.db)
fpx.add_command(client.client)
fpx.add_command(ticket.ticket)
