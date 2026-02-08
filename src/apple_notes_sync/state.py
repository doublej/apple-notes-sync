"""JSON state file management for sync tracking."""

import json
from datetime import datetime
from pathlib import Path


def task_key(task: dict) -> tuple[str, str]:
    """Unique key for a task: (heading, text)."""
    return (task["heading"], task["text"])


def load(path: Path) -> dict:
    """Load sync state from JSON file."""
    if not path.exists():
        return {"last_sync": None, "tasks": []}
    return json.loads(path.read_text())


def save(path: Path, state: dict) -> None:
    """Save sync state to JSON file."""
    state["last_sync"] = datetime.now().isoformat()
    path.write_text(json.dumps(state, indent=2) + "\n")
