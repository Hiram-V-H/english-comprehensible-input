"""add is_punctuation to article_words

Revision ID: 003
Revises: 002
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("article_words", sa.Column("is_punctuation", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("article_words", "is_punctuation")
