"""JSON state file management for sync tracking."""

import json
from datetime import datetime
from pathlib import Path

from apple_notes_sync.fileutil import atomic_write, backup


def task_key(task: dict) -> tuple[str, str]:
    """Unique key for a task: (heading, text)."""
    return (task["heading"], task["text"])


def load(path: Path) -> dict:
    """Load sync state from JSON file."""
    if not path.exists():
        return {"last_sync": None, "tasks": []}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        bak = path.with_suffix(path.suffix + ".bak")
        hint = f" (restore from {bak})" if bak.exists() else ""
        raise SystemExit(f"Corrupted state file {path}: {e}{hint}") from None


def save(path: Path, state: dict) -> None:
    """Save sync state to JSON file."""
    state["last_sync"] = datetime.now().isoformat()
    backup(path)
    atomic_write(path, json.dumps(state, indent=2) + "\n")
