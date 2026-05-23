from __future__ import annotations

from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import TimestampMixin


class Book(Base, TimestampMixin):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="import", server_default="import")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en", server_default="en")
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    toc_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_chapters: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    articles: Mapped[List["Article"]] = relationship(
        "Article", back_populates="book", cascade="all, delete-orphan",
        order_by="Article.chapter_index",
    )

    def __repr__(self) -> str:
        return f"<Book id={self.id} title={self.title!r}>"
