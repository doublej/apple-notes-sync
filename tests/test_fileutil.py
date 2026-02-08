"""Tests for file utilities: backup and atomic write."""

from pathlib import Path

from apple_notes_sync.fileutil import atomic_write, backup


def test_backup_creates_bak(tmp_path: Path):
    src = tmp_path / "data.json"
    src.write_text("original")
    bak = backup(src)
    assert bak is not None
    assert bak.name == "data.json.bak"
    assert bak.read_text() == "original"


def test_backup_missing_file(tmp_path: Path):
    result = backup(tmp_path / "nonexistent.json")
    assert result is None


def test_atomic_write(tmp_path: Path):
    target = tmp_path / "out.json"
    atomic_write(target, '{"ok": true}\n')
    assert target.read_text() == '{"ok": true}\n'
    assert not (tmp_path / "out.json.tmp").exists()


def test_atomic_write_overwrites(tmp_path: Path):
    target = tmp_path / "out.json"
    target.write_text("old")
    atomic_write(target, "new")
    assert target.read_text() == "new"
