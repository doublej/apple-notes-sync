"""Shared fixtures for integration tests."""

import subprocess
import uuid

import pytest

from apple_notes_sync.reminders import _run as osascript


def _can_automate() -> bool:
    """Check if we can talk to Reminders.app (macOS + permissions)."""
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "Reminders" to return name'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


_HAS_AUTOMATION = _can_automate()


def _skip_unless_automation(item: pytest.Item) -> None:
    if item.get_closest_marker("integration") and not _HAS_AUTOMATION:
        pytest.skip("requires macOS Reminders automation")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        _skip_unless_automation(item)


@pytest.fixture()
def reminders_list():
    """Create a unique Reminders list, delete it on teardown."""
    name = f"SyncTest-{uuid.uuid4().hex[:8]}"
    osascript(f'''
        tell application "Reminders"
            make new list with properties {{name:"{name}"}}
        end tell
    ''')
    yield name
    try:
        osascript(f'''
            tell application "Reminders"
                if exists list "{name}" then delete list "{name}"
            end tell
        ''')
    except Exception:
        pass


@pytest.fixture()
def notes_env():
    """Create a test note (so protobuf path works), yield (folder, title), delete on teardown."""
    folder = f"SyncTest-{uuid.uuid4().hex[:8]}"
    title = "Integration Test"
    # Pre-create the note so update_note_data finds it in the DB (avoids HTML fallback)
    osascript(f'''
        tell application "Notes"
            if not (exists folder "{folder}") then
                make new folder with properties {{name:"{folder}"}}
            end if
            make new note at folder "{folder}" with properties {{name:"{title}", body:""}}
        end tell
    ''')
    yield folder, title
    _delete_notes_folder(folder)


def _delete_notes_folder(folder: str) -> None:
    """Delete a Notes folder via AppleScript + SQLite DB cleanup."""
    # AppleScript deletion
    subprocess.run(
        [
            "osascript",
            "-e",
            f'''
            tell application "Notes"
                if exists folder "{folder}" then delete folder "{folder}"
            end tell
        ''',
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Also mark for deletion in the DB so iCloud doesn't sync it back
    _cleanup_notes_db(folder)


def _cleanup_notes_db(folder: str) -> None:
    """Mark test folder and its notes as deleted in the Notes SQLite DB."""
    import sqlite3
    from pathlib import Path

    db_path = (
        Path.home() / "Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"
    )
    if not db_path.exists():
        return
    try:
        db = sqlite3.connect(str(db_path))
        db.execute(
            """UPDATE ZICCLOUDSYNCINGOBJECT SET ZMARKEDFORDELETION = 1
               WHERE ZFOLDER IN (
                   SELECT Z_PK FROM ZICCLOUDSYNCINGOBJECT WHERE ZTITLE2 = ?
               )""",
            (folder,),
        )
        db.execute(
            "UPDATE ZICCLOUDSYNCINGOBJECT SET ZMARKEDFORDELETION = 1 WHERE ZTITLE2 = ?",
            (folder,),
        )
        db.commit()
        db.close()
    except sqlite3.Error:
        pass


@pytest.fixture()
def md_file(tmp_path):
    """Write test markdown and yield the Path."""
    md = tmp_path / "tasks.md"
    md.write_text(
        "## Tasks\n\n"
        "### Work\n\n"
        "- [ ] **Email client**: Reply to open threads\n"
        "- [ ] **Deploy**: Push staging build\n"
        "- [x] **Review**: Check PR comments\n"
    )
    return md


@pytest.fixture()
def state_file(tmp_path):
    """Yield a state file path (starts empty)."""
    return tmp_path / ".tasks-sync.json"
