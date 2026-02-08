"""Tests for state file management."""

from pathlib import Path

from apple_notes_sync.state import load, save, task_key


def test_task_key():
    task = {"heading": "Work", "text": "Do thing"}
    assert task_key(task) == ("Work", "Do thing")


def test_load_missing_file(tmp_path: Path):
    state = load(tmp_path / "nonexistent.json")
    assert state == {"last_sync": None, "tasks": []}


def test_save_and_load(tmp_path: Path):
    path = tmp_path / "state.json"
    state = {"last_sync": None, "tasks": [{"heading": "A", "text": "B"}]}
    save(path, state)

    loaded = load(path)
    assert loaded["tasks"] == [{"heading": "A", "text": "B"}]
    assert loaded["last_sync"] is not None
