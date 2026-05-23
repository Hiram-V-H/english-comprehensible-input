"""add toc_json column to books

Revision ID: 006
Revises: 005
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("books") as batch_op:
        batch_op.add_column(sa.Column("toc_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("books") as batch_op:
        batch_op.drop_column("toc_json")
