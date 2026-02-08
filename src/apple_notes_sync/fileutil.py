"""File utilities: backup and atomic write."""

import os
import shutil
from pathlib import Path


def backup(path: Path) -> Path | None:
    """Copy file to file.bak before overwriting. Returns backup path, or None if source missing."""
    if not path.exists():
        return None
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    return bak


def atomic_write(path: Path, content: str) -> None:
    """Write to temp file then atomically replace. Prevents half-written files."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    os.replace(tmp, path)
