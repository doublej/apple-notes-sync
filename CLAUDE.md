# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- Python 3.12, uv, ruff, mypy, pytest
- CLI framework: Click
- No external dependencies beyond Click — stdlib only for AppleScript/protobuf/SQLite

## Commands

Use `just` as the task runner:

- `just check` — run all checks (loc-check + lint + format-check + typecheck + test)
- `just fix` — auto-fix lint + format in one step
- `just test` — run tests (unit + integration)
- `just test-unit` — run unit tests only (skip integration)
- `just run` — run the CLI
- `just sync` / `status` — top-level sync shortcuts
- `just reminders-push` / `reminders-pull` / `notes-push` — targeted sync shortcuts
- Single test: `uv run pytest tests/test_foo.py::test_name -v`

## Conventions

- src/ layout with hatchling build backend
- Module name: `apple_notes_sync`, entry point: `apple_notes_sync.cli:main`
- Keep functions small (5-10 lines target, 20 max)
- File length limits: warn >300, error >400 lines
- See [agent.md](agent.md) for common tasks and agent boundaries

## Architecture

### Data Flow

```
Markdown file  <->  State (.tasks-sync.json)  <->  Reminders.app (AppleScript)
                         |
                         +---->  Notes.app (protobuf or HTML)
```

- **Reminders**: two-way sync via AppleScript (`reminders.py`). State file tracks `reminder_id` per task.
- **Notes**: one-way push. Two write strategies in `notes.py`:
  1. **Native protobuf** (preferred): writes gzipped protobuf directly to Notes SQLite DB. Produces real interactive checklists. Notes detects the DB change automatically.
  2. **HTML fallback**: creates/updates notes via AppleScript when protobuf fails (e.g., note doesn't exist yet).
- **State** (`state.py`): JSON file mapping `(heading, text)` -> reminder ID + completion status. Used as three-way merge anchor.
- **Sync logic** (`sync.py`): `push_reminders` and `push_notes` are independent. `pull` only reads from Reminders.

### CLI Structure

`cli.py` uses Click groups with shared `_opt_*` decorators applied per command:

```
apple-notes-sync reminders push    # --file --state --reminders-list --dry-run
apple-notes-sync reminders pull    # --file --state --reminders-list --dry-run
apple-notes-sync notes push        # --file --notes-folder --notes-title --dry-run
apple-notes-sync sync              # all options (reminders push + notes push + pull)
apple-notes-sync status            # --file --state --reminders-list
```

### Markdown Format

Tasks are parsed from a `## Tasks` section with `### Heading` subsections:

```markdown
## Tasks

### Section Name

- [ ] **Bold label**: task description
- [x] Completed task
```

Reminder names: `[Section Name] Bold label` (bold text extracted from `**...**`).

## Critical Technical Details

### Apple Notes Protobuf

Notes SQLite: `~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite`, table `ZICNOTEDATA.ZDATA` (gzipped protobuf).

Key protobuf structure (`protobuf.py` encodes, `notes.py` assembles):
- **f3**: CRDT text runs with sentinel `0xFFFFFFFF` marking end
- **f4**: Replica metadata (UUID + version counters)
- **f5**: Paragraph styles — `style=0` for title, `style=103` for todo/checkbox (UUID + done flag)
- Document wrapping: `Document(f1=0, f2=Version(f1=0, f2=0, f3=String(f2=text, f3=runs, f4=meta, f5=paragraphs)))`
- Reference: https://github.com/dunhamsteve/notesutils/blob/master/notes.md

### AppleScript

All Apple automation via `subprocess.run(["osascript", "-e", script])` with 30s timeout. `reminders._run` is also used by `notes.py` for the HTML fallback.

### State File (`.tasks-sync.json`)

```json
{
  "last_sync": "2026-02-08T18:10:01.055772",
  "tasks": [
    {"heading": "Section Name", "text": "**Bold label**: task description", "completed": false, "reminder_id": "x-apple-reminder://UUID"}
  ]
}
```
