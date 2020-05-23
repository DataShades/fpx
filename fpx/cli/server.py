import click


@click.group()
def server():
    pass


@server.command()
def run():
    from fpx.app import run_app

    run_app()
