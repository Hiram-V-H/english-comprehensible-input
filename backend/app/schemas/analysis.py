from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class AnalysisResultOut(BaseModel):
    algorithm_name: str
    score: float
    label: str
    details: Dict[str, Any]


class ArticleAnalysisOut(BaseModel):
    article_id: int
    title: str
    word_count: Optional[int] = None
    unknown_word_count: Optional[int] = None
    unknown_word_density: Optional[float] = None
    i_plus_one_score: Optional[float] = None
    difficulty_score: Optional[float] = None
