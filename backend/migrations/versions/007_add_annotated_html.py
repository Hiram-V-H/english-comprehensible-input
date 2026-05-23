"""add annotated_html column to articles

Revision ID: 007
Revises: 006
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("articles") as batch_op:
        batch_op.add_column(sa.Column("annotated_html", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("articles") as batch_op:
        batch_op.drop_column("annotated_html")
