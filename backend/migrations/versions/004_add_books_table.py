"""add books table and article book/chapter fields

Revision ID: 004
Revises: 003
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Books table
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("author", sa.String(500), nullable=True),
        sa.Column("source_path", sa.String(1000), nullable=True),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="import"),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("total_chapters", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_books_sha256", "books", ["sha256_hash"])
    op.create_index("ix_books_title", "books", ["title"])

    # SQLite requires batch mode for ALTER TABLE with constraints
    with op.batch_alter_table("articles") as batch_op:
        batch_op.add_column(sa.Column("book_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("chapter_index", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("chapter_path", sa.String(500), nullable=True))
        batch_op.create_foreign_key(
            "fk_articles_book",
            "books", ["book_id"], ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_articles_book", ["book_id"])
        batch_op.create_index("ix_articles_chapter", ["book_id", "chapter_index"])


def downgrade() -> None:
    with op.batch_alter_table("articles") as batch_op:
        batch_op.drop_index("ix_articles_chapter")
        batch_op.drop_index("ix_articles_book")
        batch_op.drop_constraint("fk_articles_book", type_="foreignkey")
        batch_op.drop_column("chapter_path")
        batch_op.drop_column("chapter_index")
        batch_op.drop_column("book_id")
    op.drop_table("books")
