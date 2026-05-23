from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ImportRecord(Base):
    __tablename__ = "import_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    article_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("articles.id", ondelete="SET NULL"), nullable=True,
    )
    import_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="success",
        server_default="success",
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_modified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<ImportRecord id={self.id} status={self.import_status!r}>"
