"""Markdown task parsing and writing."""

import re


def parse_tasks(content: str) -> list[dict]:
    """Parse ## Tasks section into structured tasks."""
    match = re.search(
        r"^## Tasks\n(.*?)(?=^## |\Z)", content, re.MULTILINE | re.DOTALL
    )
    if not match:
        return []

    tasks = []
    current_heading = "Unsorted"

    for line in match.group(1).splitlines():
        heading_match = re.match(r"^### (.+)", line)
        if heading_match:
            current_heading = heading_match.group(1).strip()
            continue

        task_match = re.match(r"^- \[([ xX])\] (.+)", line)
        if task_match:
            completed = task_match.group(1).lower() == "x"
            text = task_match.group(2).strip()
            tasks.append({
                "heading": current_heading,
                "text": text,
                "completed": completed,
            })

    return tasks


def extract_reminder_name(text: str) -> str:
    """Extract bold text as reminder name, or use first 50 chars."""
    bold = re.search(r"\*\*(.+?)\*\*", text)
    return bold.group(1) if bold else text[:50]


def update_task(content: str, text: str, completed: bool) -> str:
    """Update a single task's checkbox state in markdown."""
    new_check = "- [x]" if completed else "- [ ]"
    escaped = re.escape(text)
    pattern = rf"^- \[[ xX]\] {escaped}$"
    match = re.search(pattern, content, re.MULTILINE)
    if match:
        return content.replace(match.group(0), f"{new_check} {text}", 1)
    return content


def append_task(content: str, heading: str, text: str) -> str:
    """Append a new task under the given heading in ## Tasks."""
    task_line = f"- [ ] {text}"

    heading_pattern = rf"^### {re.escape(heading)}$"
    heading_match = re.search(heading_pattern, content, re.MULTILINE)

    if heading_match:
        pos = heading_match.end()
        next_section = re.search(r"^(?:###? )", content[pos:], re.MULTILINE)
        insert_pos = pos + next_section.start() if next_section else len(content)
        return (
            content[:insert_pos].rstrip()
            + "\n"
            + task_line
            + "\n"
            + content[insert_pos:]
        )

    # Heading doesn't exist — add before ## Phase or at end of Tasks
    phase_match = re.search(r"^## Phase", content, re.MULTILINE)
    insert_pos = phase_match.start() if phase_match else len(content)

    block = f"\n### {heading}\n\n{task_line}\n\n"
    return content[:insert_pos] + block + content[insert_pos:]
