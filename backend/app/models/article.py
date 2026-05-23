from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import TimestampMixin


class Article(Base, TimestampMixin):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="import",
        server_default="import",
    )
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    frontmatter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unknown_word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    unknown_word_density: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    i_plus_one_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    read_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Book chapter support
    book_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("books.id", ondelete="SET NULL"), nullable=True)
    chapter_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chapter_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    book: Mapped[Optional["Book"]] = relationship("Book", back_populates="articles")
    article_words: Mapped[List["ArticleWord"]] = relationship(
        "ArticleWord", back_populates="article", cascade="all, delete-orphan",
    )
    highlights: Mapped[List["Highlight"]] = relationship(
        "Highlight", back_populates="article", cascade="all, delete-orphan",
    )
    annotations: Mapped[List["Annotation"]] = relationship(
        "Annotation", back_populates="article", cascade="all, delete-orphan",
    )
    tags: Mapped[List["ArticleTag"]] = relationship(
        "ArticleTag", back_populates="article", cascade="all, delete-orphan",
    )
    reading_sessions: Mapped[List["ReadingSession"]] = relationship(
        "ReadingSession", back_populates="article", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Article id={self.id} title={self.title!r}>"


class ArticleWord(Base):
    __tablename__ = "article_words"
    __table_args__ = (
        UniqueConstraint("article_id", "position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("articles.id", ondelete="CASCADE"))
    word_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("words.id", ondelete="SET NULL"), nullable=True)
    word_text: Mapped[str] = mapped_column(String(255), nullable=False)
    word_lower: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    sentence_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_unknown_at_import: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_punctuation: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    article: Mapped["Article"] = relationship("Article", back_populates="article_words")
    word: Mapped[Optional["Word"]] = relationship("Word", back_populates="article_words")

    def __repr__(self) -> str:
        return f"<ArticleWord pos={self.position} word={self.word_text!r}>"
