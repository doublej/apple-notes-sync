"""Tests for state file management."""

from pathlib import Path

import pytest

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


def test_load_corrupted_json(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_text("{broken json")
    with pytest.raises(SystemExit, match="Corrupted state file"):
        load(path)


def test_load_corrupted_mentions_bak(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_text("{broken")
    bak = path.with_suffix(".json.bak")
    bak.write_text('{"last_sync": null, "tasks": []}')
    with pytest.raises(SystemExit, match=r"restore from.*\.bak"):
        load(path)


def test_save_creates_backup(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_text('{"last_sync": null, "tasks": []}')
    save(path, {"last_sync": None, "tasks": []})
    bak = path.with_suffix(".json.bak")
    assert bak.exists()
    assert "tasks" in bak.read_text()
