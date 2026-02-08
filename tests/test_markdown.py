"""Tests for markdown task parsing and writing."""

from apple_notes_sync.markdown import (
    append_task,
    extract_reminder_name,
    parse_tasks,
    update_task,
)

SAMPLE_MD = """\
# My Doc

## Tasks

### Work

- [ ] **Design review**: prepare slides
- [x] **Standup**: done

### Personal

- [ ] Buy groceries

## Phase 2
"""


def test_parse_tasks():
    tasks = parse_tasks(SAMPLE_MD)
    assert len(tasks) == 3
    assert tasks[0] == {
        "heading": "Work",
        "text": "**Design review**: prepare slides",
        "completed": False,
    }
    assert tasks[1]["completed"] is True
    assert tasks[2]["heading"] == "Personal"


def test_parse_tasks_no_section():
    assert parse_tasks("# Just a title\n\nSome content\n") == []


def test_extract_reminder_name_bold():
    assert extract_reminder_name("**Design review**: prepare slides") == "Design review"


def test_extract_reminder_name_no_bold():
    assert extract_reminder_name("Buy groceries") == "Buy groceries"


def test_update_task_check():
    result = update_task(SAMPLE_MD, "**Design review**: prepare slides", True)
    assert "- [x] **Design review**: prepare slides" in result


def test_update_task_uncheck():
    result = update_task(SAMPLE_MD, "**Standup**: done", False)
    assert "- [ ] **Standup**: done" in result


def test_update_task_not_found():
    result = update_task(SAMPLE_MD, "nonexistent task", True)
    assert result == SAMPLE_MD


def test_append_task_existing_heading():
    result = append_task(SAMPLE_MD, "Work", "New task")
    assert "- [ ] New task" in result
    # Should appear after existing Work tasks
    assert result.index("- [ ] New task") > result.index("**Standup**")


def test_append_task_new_heading():
    result = append_task(SAMPLE_MD, "Health", "Go running")
    assert "### Health" in result
    assert "- [ ] Go running" in result
    # New heading should appear before ## Phase 2
    assert result.index("### Health") < result.index("## Phase 2")
