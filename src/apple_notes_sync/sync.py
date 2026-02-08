"""Core sync logic: push, pull, and status operations."""

import re

from apple_notes_sync.markdown import (
    append_task,
    extract_reminder_name,
    parse_tasks,
    update_task,
)
from apple_notes_sync.notes import create_or_update_note, update_note_data
from apple_notes_sync.reminders import (
    create_list,
    create_reminder,
    list_reminders,
    set_completed,
)
from apple_notes_sync.state import task_key


def tasks_to_sections(tasks: list[dict]) -> list[dict]:
    """Group flat tasks into sections for Notes protobuf."""
    sections: list[dict] = []
    current: dict | None = None
    for task in tasks:
        if not current or current["heading"] != task["heading"]:
            current = {"heading": task["heading"], "tasks": []}
            sections.append(current)
        current["tasks"].append({"text": task["text"], "completed": task["completed"]})
    return sections


def build_notes_html(tasks: list[dict]) -> str:
    """Build HTML for Apple Notes from task list."""
    html_parts = ["<h1>Tasks</h1>"]
    current_heading = None

    for task in tasks:
        if task["heading"] != current_heading:
            if current_heading:
                html_parts.append("</ul>")
            current_heading = task["heading"]
            html_parts.append(f"<div><b>{current_heading}</b></div>")
            html_parts.append('<ul class="Apple-dash-list">')

        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", task["text"])
        check = "\u2611" if task["completed"] else "\u2610"
        html_parts.append(f"<li>{check} {text}</li>")

    if current_heading:
        html_parts.append("</ul>")

    return "\n".join(html_parts)


def push(
    content: str,
    state: dict,
    reminders_list: str,
    notes_folder: str,
    notes_title: str,
) -> dict:
    """Push markdown tasks to Reminders + Notes. Returns updated state."""
    tasks = parse_tasks(content)
    if not tasks:
        print("No tasks found in ## Tasks section")
        return state

    create_list(reminders_list)
    state_by_key = {task_key(st): st for st in state["tasks"]}
    md_keys: set[tuple[str, str]] = set()

    for task in tasks:
        key = task_key(task)
        md_keys.add(key)
        state_task = state_by_key.get(key)
        name = f"[{task['heading']}] {extract_reminder_name(task['text'])}"

        if state_task:
            if state_task["completed"] != task["completed"]:
                set_completed(reminders_list, state_task["reminder_id"], task["completed"])
                state_task["completed"] = task["completed"]
                print(f"  updated: {name} -> {'done' if task['completed'] else 'todo'}")
            else:
                print(f"  unchanged: {name}")
        else:
            rid = create_reminder(reminders_list, name, task["text"])
            if task["completed"]:
                set_completed(reminders_list, rid, True)
            state["tasks"].append({
                "heading": task["heading"],
                "text": task["text"],
                "completed": task["completed"],
                "reminder_id": rid,
            })
            print(f"  created: {name}")

    for st in state["tasks"]:
        if task_key(st) not in md_keys:
            print(f"  removed from markdown: [{st['heading']}] {extract_reminder_name(st['text'])}")

    # Push to Notes — try native protobuf first, fall back to HTML
    sections = tasks_to_sections(tasks)
    if update_note_data(notes_folder, notes_title, sections):
        print("  pushed to Notes.app (native checklists)")
    else:
        html = build_notes_html(tasks)
        create_or_update_note(notes_folder, notes_title, html)
        print("  pushed to Notes.app (HTML fallback)")

    return state


def pull(
    content: str,
    state: dict,
    reminders_list: str,
) -> tuple[str, dict]:
    """Pull Reminders state into markdown. Returns (updated_content, updated_state)."""
    reminders = list_reminders(reminders_list)
    if not reminders:
        print("No reminders found in list")
        return content, state

    md_keys = {task_key(t) for t in parse_tasks(content)}
    state_by_rid = {st.get("reminder_id"): st for st in state["tasks"]}

    for reminder in reminders:
        state_task = state_by_rid.get(reminder["id"])

        if state_task:
            if state_task["completed"] != reminder["completed"]:
                content = update_task(content, state_task["text"], reminder["completed"])
                state_task["completed"] = reminder["completed"]
                name = extract_reminder_name(state_task["text"])
                print(f"  updated: {name} -> {'done' if reminder['completed'] else 'todo'}")
        else:
            text = reminder["body"] or reminder["name"]
            heading = "Unsorted"
            prefix_match = re.match(r"^\[(.+?)\] ", reminder["name"])
            if prefix_match:
                heading = prefix_match.group(1)

            if (heading, text) not in md_keys:
                content = append_task(content, heading, text)
                print(f"  added from Reminders: [{heading}] {reminder['name']}")

            state["tasks"].append({
                "heading": heading,
                "text": text,
                "completed": reminder["completed"],
                "reminder_id": reminder["id"],
            })

    return content, state


def show_status(
    content: str,
    state: dict,
    reminders_list: str,
) -> None:
    """Show sync state diff."""
    md_tasks = parse_tasks(content)
    reminders = list_reminders(reminders_list) if state["tasks"] else []

    print(f"Last sync: {state.get('last_sync', 'never')}")
    print(f"Markdown tasks: {len(md_tasks)}")
    print(f"State entries: {len(state['tasks'])}")
    print(f"Reminders: {len(reminders)}")

    diffs = _compute_diffs(state, reminders, md_tasks)

    if diffs:
        print(f"\nDiffs ({len(diffs)}):")
        for d in diffs:
            print(d)
    else:
        print("\nAll in sync")


def _compute_diffs(
    state: dict,
    reminders: list[dict],
    md_tasks: list[dict],
) -> list[str]:
    """Compute sync diffs between state, reminders, and markdown."""
    diffs = []
    reminder_map = {r["id"]: r for r in reminders}
    md_by_key = {task_key(mt): mt for mt in md_tasks}

    for st in state["tasks"]:
        reminder = reminder_map.get(st.get("reminder_id"))
        md_task = md_by_key.get(task_key(st))
        name = extract_reminder_name(st["text"])

        if not md_task:
            diffs.append(f"  missing from markdown: [{st['heading']}] {name}")
        elif not reminder:
            diffs.append(f"  missing from Reminders: [{st['heading']}] {name}")
        elif md_task["completed"] != reminder["completed"]:
            diffs.append(
                f"  conflict: [{st['heading']}] {name} "
                f"(md={'done' if md_task['completed'] else 'todo'}, "
                f"reminder={'done' if reminder['completed'] else 'todo'})"
            )

    state_keys = {task_key(st) for st in state["tasks"]}
    for mt in md_tasks:
        if task_key(mt) not in state_keys:
            diffs.append(
                f"  new in markdown: [{mt['heading']}] {extract_reminder_name(mt['text'])}"
            )

    return diffs
