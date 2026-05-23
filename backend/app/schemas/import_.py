from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ImportRecordOut(BaseModel):
    id: int
    source_path: str
    source_type: str
    sha256_hash: str
    article_id: Optional[int] = None
    import_status: str
    error_message: Optional[str] = None
    imported_at: datetime

    model_config = {"from_attributes": True}


class FolderImportRequest(BaseModel):
    folder_path: str
    recursive: bool = False


class PathCheckRequest(BaseModel):
    path: str


class ImportResult(BaseModel):
    article_id: int
    title: str
    status: str
    word_count: int
