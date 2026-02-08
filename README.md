# Apple Notes Sync

Two-way task sync between Markdown, Apple Reminders, and Apple Notes with native checklists

## Requirements

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)

## Getting Started

```bash
uv sync
uv run apple-notes-sync hello
```

## Common Commands

| Command | Description |
|---------|-------------|
| `uv sync` | Install dependencies |
| `uv run apple-notes-sync --help` | Show CLI help |
| `uv run pytest` | Run tests |

## Project Structure

```
src/apple_notes_sync/
  __init__.py
  cli.py         # Click CLI commands
```
