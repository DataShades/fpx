"""Create clients table

Revision ID: 6a22a6995723
Revises:
Create Date: 2020-05-23 06:21:08.517988

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6a22a6995723"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "clients",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String, unique=True, nullable=False),
    )


def downgrade():
    op.drop_table("clients")
