import os
import click

from alembic.config import Config
from alembic import command

import fpx


@click.group()
def db():
    pass


@db.command()
@click.pass_obj
def up(app):
    command.upgrade(_alembic_config(app.config), "head")
    click.secho("Success", fg="green")


@db.command()
@click.pass_obj
def down(app):
    command.downgrade(_alembic_config(app.config), "base")
    click.secho("Success", fg="green")


@db.command()
@click.pass_obj
def current(app):
    command.current(_alembic_config(app.config))


def _alembic_config(config):
    alembic = Config(
        os.path.join(os.path.dirname(fpx.__file__), "alembic.ini")
    )
    alembic.set_main_option("sqlalchemy.url", config.DB_URL)
    return alembic
