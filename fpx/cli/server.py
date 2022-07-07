import click


@click.group()
def server():
    pass


@server.command()
@click.pass_context
def run(ctx):
    from fpx.app import run_app

    run_app(ctx.obj)
