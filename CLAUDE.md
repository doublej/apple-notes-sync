# Apple Notes Sync

> Two-way task sync between Markdown, Apple Reminders, and Apple Notes with native checklists

## Stack

- Python 3.12, uv, ruff, mypy, pytest
- CLI framework: Click
- No external dependencies beyond Click — stdlib only for AppleScript/protobuf/SQLite

## Commands

Use `just` as the task runner:

- `just check` — run all checks (loc-check + lint + format-check + typecheck + test)
- `just loc-check` — check file lengths (warn >300, error >400 lines)
- `just run` — run the CLI
- `just test` — run tests
- `just lint-fix` — auto-fix lint issues
- `just format` — format code

## Project Structure

```
src/apple_notes_sync/
├── __init__.py
├── cli.py              # Click CLI entry point
├── sync.py             # Core sync logic (push/pull/status)
├── markdown.py         # Markdown task parsing and writing
├── reminders.py        # AppleScript wrapper for Reminders.app
├── notes.py            # Apple Notes integration (protobuf + HTML fallback)
├── protobuf.py         # Minimal protobuf encoder for Notes ZDATA
└── state.py            # JSON state file management
pyproject.toml
Justfile
```

## Conventions

- src/ layout with hatchling build backend
- Module name: `apple_notes_sync`
- Entry point: `apple_notes_sync.cli:main`
- Keep functions small (5-10 lines target, 20 max)
- Prefer explicit, readable code over cleverness
- Handle errors at boundaries; let unexpected errors surface

See [agent.md](agent.md) for AI coding agent workflow and guidelines.

---

## What This Tool Does

Syncs a `## Tasks` section from a markdown file with:
- **Apple Reminders** (two-way): checkbox state syncs both directions
- **Apple Notes** (one-way push): formatted mirror with native interactive checklists

### CLI Commands

```
apple-notes-sync push              # Markdown -> Reminders + Notes
apple-notes-sync pull              # Reminders -> Markdown
apple-notes-sync sync              # Full two-way (push then pull)
apple-notes-sync status            # Show sync state diff
```

### Options

- `--file PATH` — markdown file to sync (default: `Now/Current Focus.md`)
- `--state PATH` — state file location (default: `.tasks-sync.json`)
- `--reminders-list NAME` — Reminders list name (default: `Current Focus`)
- `--notes-folder NAME` — Notes folder name (default: `Current Focus`)
- `--notes-title NAME` — Notes note title (default: `Tasks`)

---

## Source Code Reference

A working prototype exists at `/Users/jurrejan/Documents/development/_life/.automation/`. Port the logic from these files into the proper src/ layout:

| Prototype file | Target module | What it does |
|----------------|---------------|--------------|
| `applescript_reminders.py` | `reminders.py` | AppleScript wrapper for Reminders CRUD |
| `applescript_notes.py` (lines 1-50) | `protobuf.py` | Minimal protobuf encoder (varint, tag, field helpers) |
| `applescript_notes.py` (lines 50-145) | `notes.py` | Notes protobuf builder + SQLite writer + SIGHUP reload |
| `applescript_notes.py` (lines 145-217) | `notes.py` | HTML fallback via AppleScript |
| `sync_tasks.py` (lines 41-113) | `markdown.py` | Parse/update/append tasks in markdown |
| `sync_tasks.py` (lines 115-170) | `state.py` + `sync.py` | State file + sections grouping |
| `sync_tasks.py` (lines 172-344) | `sync.py` | Push/pull/status sync operations |

**Read each prototype file before porting.** The code is already working and tested against real Apple Notes/Reminders.

---

## Critical Technical Details

### Apple Notes Protobuf Format

Notes stores data as gzipped protobuf in SQLite at:
`~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite`

Table: `ZICNOTEDATA.ZDATA` — gzipped protobuf blob.

Key protobuf structure (reverse-engineered from existing notes):
- **f3**: CRDT text runs (replica_id, position, length, sequence)
- **f4**: Replica metadata (UUID + version counters)
- **f5**: Paragraph styles — `style=0` for title, `style=103` for todo/checkbox
- Todo entries need a UUID + done flag in f5
- Sentinel value `0xFFFFFFFF` marks end of CRDT runs
- Reference: https://github.com/dunhamsteve/notesutils/blob/master/notes.md

Document wrapping: `Document(f1=0, f2=Version(f1=0, f2=0, f3=String(f2=text, f3=runs, f4=meta, f5=paragraphs)))`

### Notes Reload

After writing to SQLite, send SIGHUP to Notes.app to force re-read:
```python
subprocess.run(["killall", "-HUP", "Notes"], capture_output=True, timeout=5)
```

SQLite WAL mode allows concurrent writes — no need to quit Notes.

### AppleScript

All Apple automation via `subprocess.run(["osascript", "-e", script])` with 30s timeout (Reminders cold-start can be slow).

### State File Format (`.tasks-sync.json`)

```json
{
  "last_sync": "2026-02-08T18:10:01.055772",
  "tasks": [
    {
      "heading": "Section Name",
      "text": "**Bold label**: task description",
      "completed": false,
      "reminder_id": "x-apple-reminder://UUID"
    }
  ]
}
```

### Markdown Format

```markdown
## Tasks

### Section Name

- [ ] **Bold label**: task description
- [x] Completed task
```

Reminder names use format: `[Section Name] Bold label` (extracted from `**bold**` in task text).

---

## Implementation Priority

1. Port `protobuf.py` first (pure functions, easily testable)
2. Port `reminders.py` (AppleScript wrapper)
3. Port `notes.py` (depends on protobuf.py)
4. Port `markdown.py` (pure functions, easily testable)
5. Port `state.py` (simple JSON load/save)
6. Port `sync.py` (orchestrates everything)
7. Wire up `cli.py` with Click commands
8. Add tests for pure functions (markdown parsing, protobuf encoding)
