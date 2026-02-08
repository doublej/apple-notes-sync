# Apple Notes Sync

> Two-way task sync between Markdown, Apple Reminders, and Apple Notes with native checklists

## Stack

- Python 3.12, uv, ruff, mypy, pytest
- CLI framework: Click
- No external dependencies beyond Click — stdlib only for AppleScript/protobuf/SQLite

## Commands

Use `just` as the task runner:

- `just check` — run all checks (loc-check + lint + format-check + typecheck + test)
- `just fix` — auto-fix lint + format in one step
- `just loc-check` — check file lengths (warn >300, error >400 lines)
- `just run` — run the CLI
- `just test` — run tests
- `just lint-fix` — auto-fix lint issues
- `just format` — format code
- `just push` / `pull` / `sync` / `status` — sync command shortcuts (pass extra args)

## Project Structure

```
src/apple_notes_sync/
├── __init__.py
├── cli.py              # Click CLI entry point
├── fileutil.py         # Backup and atomic write helpers
├── markdown.py         # Markdown task parsing and writing
├── notes.py            # Apple Notes integration (protobuf + HTML fallback)
├── protobuf.py         # Minimal protobuf encoder for Notes ZDATA
├── reminders.py        # AppleScript wrapper for Reminders.app
├── state.py            # JSON state file management
└── sync.py             # Core sync logic (push/pull/status)
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
- `--dry-run` — preview changes without writing anything

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
