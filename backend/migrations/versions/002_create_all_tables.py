"""create all remaining tables

Revision ID: 002
Revises: 001
Create Date: 2026-05-22

Creates: word_notes, articles, article_words, highlights, annotations,
tags, annotation_tags, article_tags, word_tags, import_records, reading_sessions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # word_notes
    op.create_table(
        "word_notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("words.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note_type", sa.String(30), nullable=False, server_default="general"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_word_notes_word_id", "word_notes", ["word_id"])

    # articles
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source_path", sa.String(1000), nullable=True),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="import"),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("sha256_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("frontmatter", sa.Text(), nullable=True),
        sa.Column("difficulty_score", sa.Float(), nullable=True),
        sa.Column("unknown_word_count", sa.Integer(), nullable=True),
        sa.Column("unknown_word_density", sa.Float(), nullable=True),
        sa.Column("i_plus_one_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_read_at", sa.DateTime(), nullable=True),
        sa.Column("read_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
    )
    op.create_index("ix_articles_sha256", "articles", ["sha256_hash"], unique=True)
    op.create_index("ix_articles_difficulty", "articles", ["difficulty_score"])
    op.create_index("ix_articles_created", "articles", ["created_at"])
    op.create_index("ix_articles_last_read", "articles", ["last_read_at"])

    # article_words
    op.create_table(
        "article_words",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("words.id", ondelete="SET NULL"), nullable=True),
        sa.Column("word_text", sa.String(255), nullable=False),
        sa.Column("word_lower", sa.String(255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("sentence_index", sa.Integer(), nullable=True),
        sa.Column("is_unknown_at_import", sa.Boolean(), nullable=True),
        sa.UniqueConstraint("article_id", "position"),
    )
    op.create_index("ix_article_words_article", "article_words", ["article_id"])
    op.create_index("ix_article_words_word", "article_words", ["word_id"])
    op.create_index("ix_article_words_lower", "article_words", ["word_lower"])

    # highlights
    op.create_table(
        "highlights",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(100), nullable=False, server_default="default"),
        sa.Column("highlight_type", sa.String(30), nullable=False, server_default="word"),
        sa.Column("anchor_type", sa.String(30), nullable=False, server_default="text_offset"),
        sa.Column("start_char_offset", sa.Integer(), nullable=True),
        sa.Column("end_char_offset", sa.Integer(), nullable=True),
        sa.Column("start_word_position", sa.Integer(), nullable=True),
        sa.Column("end_word_position", sa.Integer(), nullable=True),
        sa.Column("selected_text", sa.Text(), nullable=False),
        sa.Column("color", sa.String(20), nullable=False, server_default="#FFEB3B"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_highlights_article", "highlights", ["article_id"])
    op.create_index("ix_highlights_type", "highlights", ["highlight_type"])
    op.create_index("ix_highlights_offsets", "highlights", ["article_id", "start_char_offset", "end_char_offset"])

    # annotations
    op.create_table(
        "annotations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("highlight_id", sa.Integer(), sa.ForeignKey("highlights.id", ondelete="SET NULL"), nullable=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("words.id", ondelete="SET NULL"), nullable=True),
        sa.Column("annotation_type", sa.String(30), nullable=False, server_default="note"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("rich_content", sa.Text(), nullable=True),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_annotations_article", "annotations", ["article_id"])
    op.create_index("ix_annotations_highlight", "annotations", ["highlight_id"])
    op.create_index("ix_annotations_word", "annotations", ["word_id"])
    op.create_index("ix_annotations_type", "annotations", ["annotation_type"])

    # tags
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # annotation_tags
    op.create_table(
        "annotation_tags",
        sa.Column("annotation_id", sa.Integer(), sa.ForeignKey("annotations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )

    # article_tags
    op.create_table(
        "article_tags",
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )

    # word_tags
    op.create_table(
        "word_tags",
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("words.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )

    # import_records
    op.create_table(
        "import_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_path", sa.String(1000), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("import_status", sa.String(20), nullable=False, server_default="success"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("file_modified_at", sa.DateTime(), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_import_records_hash", "import_records", ["sha256_hash"])
    op.create_index("ix_import_records_path", "import_records", ["source_path"])

    # reading_sessions
    op.create_table(
        "reading_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("words_looked_up", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("word_position_stopped", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
    )
    op.create_index("ix_reading_sessions_article", "reading_sessions", ["article_id"])


def downgrade() -> None:
    op.drop_table("reading_sessions")
    op.drop_table("import_records")
    op.drop_table("word_tags")
    op.drop_table("article_tags")
    op.drop_table("annotation_tags")
    op.drop_table("tags")
    op.drop_table("annotations")
    op.drop_table("highlights")
    op.drop_table("article_words")
    op.drop_table("articles")
    op.drop_table("word_notes")
