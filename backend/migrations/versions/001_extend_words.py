"""extend words table

Revision ID: 001
Revises: None
Create Date: 2026-05-22

Transforms the legacy words table (word TEXT PK, status TEXT) into the new
extended schema with integer PK, word_lower unique index, familiarity tracking,
and encounter metadata. Preserves all 2,971 existing rows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename old table
    op.rename_table("words", "words_old")

    # 2. Create new words table with full schema
    op.create_table(
        "words",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("word", sa.String(255), nullable=False),
        sa.Column("word_lower", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("familiarity", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("encounter_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_encountered", sa.DateTime(), nullable=True),
        sa.Column("first_seen", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("pronunciation", sa.String(100), nullable=True),
        sa.Column("lemma", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 3. Create indexes
    op.create_index("ix_words_word_lower", "words", ["word_lower"], unique=True)
    op.create_index("ix_words_status", "words", ["status"])
    op.create_index("ix_words_lemma", "words", ["lemma"])
    op.create_index("ix_words_familiarity", "words", ["familiarity"])

    # 4. Copy existing rows. All existing words are "known", set familiarity=1.0
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT word, status FROM words_old")).fetchall()
    insert_data = [
        {
            "word": row[0],
            "word_lower": row[0].lower(),
            "status": row[1],
            "familiarity": 1.0,
            "encounter_count": 0,
        }
        for row in rows
    ]
    if insert_data:
        conn.execute(
            sa.text(
                """INSERT INTO words (word, word_lower, status, familiarity,
                   encounter_count)
                   VALUES (:word, :word_lower, :status, :familiarity,
                   :encounter_count)"""
            ),
            insert_data,
        )

    # 5. Drop old table
    op.drop_table("words_old")


def downgrade() -> None:
    op.drop_index("ix_words_familiarity", table_name="words")
    op.drop_index("ix_words_lemma", table_name="words")
    op.drop_index("ix_words_status", table_name="words")
    op.drop_index("ix_words_word_lower", table_name="words")

    op.rename_table("words", "words_new")

    op.create_table(
        "words",
        sa.Column("word", sa.String(255), primary_key=True),
        sa.Column("status", sa.String(20)),
    )

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT word, status FROM words_new")).fetchall()
    if rows:
        conn.execute(
            sa.text("INSERT INTO words (word, status) VALUES (:word, :status)"),
            [{"word": r[0], "status": r[1]} for r in rows],
        )

    op.drop_table("words_new")
