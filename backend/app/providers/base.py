from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseProvider(ABC):
    """Every provider is instantiated with a config dict and validated before use."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

    @classmethod
    @abstractmethod
    def provider_name(cls) -> str:
        """Unique identifier, e.g. 'openai', 'stardict', 'txt_importer'."""
        ...

    @abstractmethod
    async def validate(self) -> bool:
        """Return True if the provider is ready to use."""
        ...

    async def health_check(self) -> Dict[str, Any]:
        ok = await self.validate()
        return {"provider": self.provider_name(), "available": ok}
