from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ArticleSummary(BaseModel):
    id: int
    title: str
    source_type: str
    word_count: Optional[int] = None
    unknown_word_count: Optional[int] = None
    unknown_word_density: Optional[float] = None
    i_plus_one_score: Optional[float] = None
    difficulty_score: Optional[float] = None
    is_archived: bool
    read_count: int
    last_read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    exam_type: Optional[str] = None
    exam_year: Optional[int] = None
    question_type: Optional[str] = None

    model_config = {"from_attributes": True}


class ArticleDetail(BaseModel):
    id: int
    title: str
    source_type: str
    source_path: Optional[str] = None
    content_text: str
    content_html: Optional[str] = None
    word_count: Optional[int] = None
    language: str
    frontmatter: Optional[str] = None
    difficulty_score: Optional[float] = None
    unknown_word_count: Optional[int] = None
    unknown_word_density: Optional[float] = None
    i_plus_one_score: Optional[float] = None
    is_archived: bool
    read_count: int
    last_read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    exam_type: Optional[str] = None
    exam_year: Optional[int] = None
    question_type: Optional[str] = None

    model_config = {"from_attributes": True}


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    is_archived: Optional[bool] = None
    exam_type: Optional[str] = None
    exam_year: Optional[int] = None
    question_type: Optional[str] = None


class ArticleContentUpdate(BaseModel):
    content_text: str = Field(..., min_length=1)
