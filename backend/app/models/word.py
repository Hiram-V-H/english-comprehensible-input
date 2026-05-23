from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import TimestampMixin


class Word(Base, TimestampMixin):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(255), nullable=False)
    word_lower: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown",
        server_default="unknown",
    )
    familiarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    encounter_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_encountered: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    pronunciation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lemma: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    word_notes: Mapped[List["WordNote"]] = relationship(
        "WordNote", back_populates="word", cascade="all, delete-orphan",
    )
    article_words: Mapped[List["ArticleWord"]] = relationship(
        "ArticleWord", back_populates="word",
    )

    def __repr__(self) -> str:
        return f"<Word id={self.id} word={self.word!r} status={self.status!r}>"


class WordNote(Base, TimestampMixin):
    __tablename__ = "word_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word_id: Mapped[int] = mapped_column(Integer, ForeignKey("words.id", ondelete="CASCADE"))
    note_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="general",
        server_default="general",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    word: Mapped["Word"] = relationship("Word", back_populates="word_notes")

    def __repr__(self) -> str:
        return f"<WordNote id={self.id} word_id={self.word_id} type={self.note_type!r}>"
