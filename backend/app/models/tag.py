from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    annotation_tags: Mapped[List["AnnotationTag"]] = relationship(
        "AnnotationTag", back_populates="tag", cascade="all, delete-orphan",
    )
    article_tags: Mapped[List["ArticleTag"]] = relationship(
        "ArticleTag", back_populates="tag", cascade="all, delete-orphan",
    )
    word_tags: Mapped[List["WordTag"]] = relationship(
        "WordTag", back_populates="tag", cascade="all, delete-orphan",
    )


class AnnotationTag(Base):
    __tablename__ = "annotation_tags"

    annotation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("annotations.id", ondelete="CASCADE"), primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True,
    )

    annotation: Mapped["Annotation"] = relationship("Annotation", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="annotation_tags")


class ArticleTag(Base):
    __tablename__ = "article_tags"

    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True,
    )

    article: Mapped["Article"] = relationship("Article", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="article_tags")


class WordTag(Base):
    __tablename__ = "word_tags"

    word_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("words.id", ondelete="CASCADE"), primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True,
    )

    word: Mapped["Word"] = relationship("Word")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="word_tags")
