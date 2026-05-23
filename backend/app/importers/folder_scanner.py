from __future__ import annotations

from pathlib import Path
from typing import List


def scan_folder(folder_path: str, recursive: bool = False) -> List[str]:
    """Scan a folder for importable files. Returns list of absolute file paths."""
    p = Path(folder_path)
    if not p.exists() or not p.is_dir():
        return []

    supported = {".txt", ".text", ".md", ".markdown"}
    files = []
    iterator = p.rglob("*") if recursive else p.glob("*")
    for f in iterator:
        if f.is_file() and f.suffix.lower() in supported:
            files.append(str(f.resolve()))
    return sorted(files)
