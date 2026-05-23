from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings

# Project root is one level above backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    database_url: str = ""
    data_dir: str = ""
    materials_raw_dir: str = ""
    materials_processed_dir: str = ""
    materials_failed_dir: str = ""
    vocabulary_source: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        data_dir = self.data_dir or str(PROJECT_ROOT / "data")
        self.database_url = self.database_url or f"sqlite+aiosqlite:///{data_dir}/database.db"
        self.data_dir = data_dir
        self.materials_raw_dir = self.materials_raw_dir or str(PROJECT_ROOT / "materials_raw")
        self.materials_processed_dir = self.materials_processed_dir or str(PROJECT_ROOT / "materials_processed")
        self.materials_failed_dir = self.materials_failed_dir or str(PROJECT_ROOT / "materials_failed")
        self.vocabulary_source = self.vocabulary_source or str(PROJECT_ROOT / "vocabulary.db")


settings = Settings()
