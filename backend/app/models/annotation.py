from __future__ import annotations

from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import TimestampMixin


class Highlight(Base, TimestampMixin):
    __tablename__ = "highlights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("articles.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    highlight_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="word",
        server_default="word",
    )
    anchor_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="text_offset",
        server_default="text_offset",
    )
    start_char_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_char_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_word_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_word_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    selected_text: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#FFEB3B")

    article: Mapped["Article"] = relationship("Article", back_populates="highlights")
    annotations: Mapped[List["Annotation"]] = relationship(
        "Annotation", back_populates="highlight", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Highlight id={self.id} type={self.highlight_type!r}>"


class Annotation(Base, TimestampMixin):
    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    highlight_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("highlights.id", ondelete="SET NULL"), nullable=True,
    )
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("articles.id", ondelete="CASCADE"))
    word_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("words.id", ondelete="SET NULL"), nullable=True,
    )
    annotation_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="note",
        server_default="note",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    rich_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    highlight: Mapped[Optional["Highlight"]] = relationship("Highlight", back_populates="annotations")
    article: Mapped["Article"] = relationship("Article", back_populates="annotations")
    tags: Mapped[List["AnnotationTag"]] = relationship(
        "AnnotationTag", back_populates="annotation", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Annotation id={self.id} type={self.annotation_type!r}>"
