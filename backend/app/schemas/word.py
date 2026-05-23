from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class WordNoteOut(BaseModel):
    id: int
    note_type: str
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WordOut(BaseModel):
    id: int
    word: str
    word_lower: str
    status: str
    familiarity: float
    encounter_count: int
    last_encountered: Optional[datetime] = None
    first_seen: datetime
    pronunciation: Optional[str] = None
    lemma: Optional[str] = None
    notes: Optional[str] = None
    word_notes: List[WordNoteOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WordSummary(BaseModel):
    id: int
    word: str
    word_lower: str
    status: str
    encounter_count: int
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WordUpdate(BaseModel):
    status: Optional[str] = None
    familiarity: Optional[float] = None
    notes: Optional[str] = None
    pronunciation: Optional[str] = None
    lemma: Optional[str] = None


class WordNoteCreate(BaseModel):
    note_type: str = "general"
    content: str


class WordNoteUpdate(BaseModel):
    note_type: Optional[str] = None
    content: Optional[str] = None


class BulkStatusUpdate(BaseModel):
    word_ids: List[int]
    new_status: str


class VocabularyStats(BaseModel):
    total: int
    unknown: int
    learning: int
    familiar: int
    known: int
    mastered: int
