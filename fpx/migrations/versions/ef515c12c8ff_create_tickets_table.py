"""Create tickets table

Revision ID: ef515c12c8ff
Revises: 6a22a6995723
Create Date: 2020-05-23 08:08:10.831315

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ef515c12c8ff"
down_revision = "6a22a6995723"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tickets",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_available", sa.Boolean, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )


def downgrade():
    op.drop_table("tickets")
