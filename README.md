# Apple Notes Sync

Two-way task sync between Markdown, Apple Reminders, and Apple Notes with native checklists.

## Requirements

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)
- [just](https://github.com/casey/just) (task runner)
- macOS with Automation permissions for Reminders.app and Notes.app

## Getting Started

```bash
uv sync
uv run apple-notes-sync --help
```

## CLI Commands

```
apple-notes-sync push       # Markdown -> Reminders + Notes
apple-notes-sync pull       # Reminders -> Markdown
apple-notes-sync sync       # Full two-way (push then pull)
apple-notes-sync status     # Show sync state diff
```

## Development

| Command | Description |
|---------|-------------|
| `just check` | Run all checks (lint + format + typecheck + test) |
| `just run` | Run the CLI |
| `just test` | Run tests |
| `just lint-fix` | Auto-fix lint issues |
| `just format` | Format code |

## Project Structure

```
src/apple_notes_sync/
├── cli.py              # Click CLI entry point
├── fileutil.py         # Backup and atomic write helpers
├── markdown.py         # Markdown task parsing and writing
├── notes.py            # Apple Notes integration (protobuf + HTML fallback)
├── protobuf.py         # Minimal protobuf encoder for Notes ZDATA
├── reminders.py        # AppleScript wrapper for Reminders.app
├── state.py            # JSON state file management
└── sync.py             # Core sync logic (push/pull/status)
```
