"""add options column to ticket table

Revision ID: ac8a8750d3e2
Revises: ef515c12c8ff
Create Date: 2021-11-05 12:44:46.657903

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ac8a8750d3e2"
down_revision = "ef515c12c8ff"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "tickets",
        sa.Column("options", sa.JSON, nullable=False, server_default="{}"),
    )


def downgrade():
    op.drop_column("tickets", "options")
