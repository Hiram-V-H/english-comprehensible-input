from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class AnalysisResult:
    algorithm_name: str
    score: float
    label: str
    details: Dict[str, Any] = field(default_factory=dict)


class AnalysisAlgorithm(ABC):
    @classmethod
    @abstractmethod
    def name(cls) -> str:
        ...

    @abstractmethod
    async def analyze(self, article_id: int, *, db: AsyncSession) -> AnalysisResult:
        ...
