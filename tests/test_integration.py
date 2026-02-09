"""Integration tests — exercise real Apple Reminders and Notes sync."""

import pytest

from apple_notes_sync.markdown import update_task
from apple_notes_sync.reminders import (
    create_reminder,
    list_reminders,
    set_completed,
)
from apple_notes_sync.state import load, save
from apple_notes_sync.sync import pull, push_notes, push_reminders

pytestmark = pytest.mark.integration


def _state(path):
    return load(path) if path.exists() else {"last_sync": None, "tasks": []}


# -- Reminders push ----------------------------------------------------------


def test_push_creates_reminders(md_file, state_file, reminders_list):
    content = md_file.read_text()
    state = _state(state_file)

    state = push_reminders(content, state, reminders_list)
    save(state_file, state)

    assert len(state["tasks"]) == 3
    assert all(t["reminder_id"] for t in state["tasks"])

    reminders = list_reminders(reminders_list)
    assert len(reminders) == 3

    completed = [r for r in reminders if r["completed"]]
    assert len(completed) == 1


# -- Pull after toggle -------------------------------------------------------


def test_pull_reflects_toggled_completion(md_file, state_file, reminders_list):
    content = md_file.read_text()
    state = _state(state_file)
    state = push_reminders(content, state, reminders_list)
    save(state_file, state)

    # Toggle first unchecked reminder to completed
    unchecked = [t for t in state["tasks"] if not t["completed"]]
    target = unchecked[0]
    set_completed(reminders_list, target["reminder_id"], True)

    state = load(state_file)
    content, state = pull(content, state, reminders_list)
    save(state_file, state)

    assert f"- [x] {target['text']}" in content
    pulled = next(t for t in state["tasks"] if t["text"] == target["text"])
    assert pulled["completed"] is True


# -- Add task then push ------------------------------------------------------


def test_add_task_then_push(md_file, state_file, reminders_list):
    content = md_file.read_text()
    state = _state(state_file)
    state = push_reminders(content, state, reminders_list)
    save(state_file, state)

    assert len(state["tasks"]) == 3

    # Append a new task
    md_file.write_text(content.rstrip() + "\n- [ ] **Docs**: Update changelog\n")
    content = md_file.read_text()
    state = load(state_file)
    state = push_reminders(content, state, reminders_list)
    save(state_file, state)

    assert len(state["tasks"]) == 4
    assert len(list_reminders(reminders_list)) == 4


# -- Toggle in markdown then push --------------------------------------------


def test_toggle_in_markdown_then_push(md_file, state_file, reminders_list):
    content = md_file.read_text()
    state = _state(state_file)
    state = push_reminders(content, state, reminders_list)
    save(state_file, state)

    # Check off the first task in markdown
    first = state["tasks"][0]
    content = update_task(content, first["text"], True)
    md_file.write_text(content)

    state = load(state_file)
    state = push_reminders(content, state, reminders_list)
    save(state_file, state)

    reminders = list_reminders(reminders_list)
    toggled = next(r for r in reminders if r["id"] == first["reminder_id"])
    assert toggled["completed"] is True


# -- External reminder pulled into markdown ----------------------------------


def test_external_reminder_pulled_into_markdown(md_file, state_file, reminders_list):
    content = md_file.read_text()
    state = _state(state_file)
    state = push_reminders(content, state, reminders_list)
    save(state_file, state)

    # Create a reminder externally (matching the [Heading] Name convention)
    create_reminder(reminders_list, "[Work] Standup", "Join daily standup")

    state = load(state_file)
    content, state = pull(content, state, reminders_list)
    save(state_file, state)

    assert "Join daily standup" in content


# -- Notes push --------------------------------------------------------------


def test_push_notes_creates_note(md_file, notes_env, capsys):
    folder, title = notes_env
    content = md_file.read_text()

    push_notes(content, folder, title)

    captured = capsys.readouterr().out
    assert "native checklists" in captured


# -- Full sync roundtrip -----------------------------------------------------


def test_full_sync_roundtrip(md_file, state_file, reminders_list, notes_env, capsys):
    folder, title = notes_env
    content = md_file.read_text()
    state = _state(state_file)

    # Push reminders + notes
    state = push_reminders(content, state, reminders_list)
    save(state_file, state)
    push_notes(content, folder, title)

    assert "native checklists" in capsys.readouterr().out

    # Toggle a reminder externally
    target = state["tasks"][0]
    original_completed = target["completed"]
    set_completed(reminders_list, target["reminder_id"], not original_completed)

    # Pull
    state = load(state_file)
    content, state = pull(content, state, reminders_list)
    save(state_file, state)

    # Verify markdown reflects the toggle
    expected_check = "- [x]" if not original_completed else "- [ ]"
    assert f"{expected_check} {target['text']}" in content

    # Verify state is consistent
    pulled = next(t for t in state["tasks"] if t["text"] == target["text"])
    assert pulled["completed"] is (not original_completed)

    # Verify reminders still match
    reminders = list_reminders(reminders_list)
    assert len(reminders) == 3
