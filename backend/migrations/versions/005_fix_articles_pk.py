"""fix articles primary key after batch migration

Revision ID: 005
Revises: 004
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Recreate articles table with proper PK, preserving data."""
    # Create new table with correct schema including PK + autoincrement
    op.execute("""
        CREATE TABLE articles_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(500) NOT NULL,
            source_path VARCHAR(1000),
            source_type VARCHAR(30) DEFAULT 'import' NOT NULL,
            content_text TEXT NOT NULL,
            content_html TEXT,
            word_count INTEGER,
            language VARCHAR(10) DEFAULT 'en' NOT NULL,
            sha256_hash VARCHAR(64) NOT NULL UNIQUE,
            frontmatter TEXT,
            difficulty_score FLOAT,
            unknown_word_count INTEGER,
            unknown_word_density FLOAT,
            i_plus_one_score FLOAT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            last_read_at DATETIME,
            read_count INTEGER DEFAULT 0 NOT NULL,
            is_archived BOOLEAN DEFAULT FALSE NOT NULL,
            book_id INTEGER,
            chapter_index INTEGER,
            chapter_path VARCHAR(500),
            FOREIGN KEY(book_id) REFERENCES books (id) ON DELETE SET NULL
        )
    """)
    # Copy data
    op.execute("INSERT INTO articles_new SELECT * FROM articles")
    # Drop old table
    op.execute("DROP TABLE articles")
    # Rename
    op.execute("ALTER TABLE articles_new RENAME TO articles")
    # Recreate indexes
    op.create_index("ix_articles_sha256", "articles", ["sha256_hash"], unique=True)
    op.create_index("ix_articles_difficulty", "articles", ["difficulty_score"])
    op.create_index("ix_articles_created", "articles", ["created_at"])
    op.create_index("ix_articles_last_read", "articles", ["last_read_at"])
    op.create_index("ix_articles_book", "articles", ["book_id"])
    op.create_index("ix_articles_chapter", "articles", ["book_id", "chapter_index"])


def downgrade() -> None:
    pass
