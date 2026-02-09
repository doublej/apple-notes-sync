"""Click CLI entry point for apple-notes-sync."""

from pathlib import Path

import click

from apple_notes_sync import state as state_mod
from apple_notes_sync.fileutil import atomic_write, backup
from apple_notes_sync.sync import pull, push_notes, push_reminders, show_status

DEFAULT_FILE = Path("Now/Current Focus.md")
DEFAULT_STATE = Path(".tasks-sync.json")
DEFAULT_REMINDERS_LIST = "Current Focus"
DEFAULT_NOTES_FOLDER = "Current Focus"
DEFAULT_NOTES_TITLE = "Tasks"

# -- shared option decorators ------------------------------------------------

_opt_file = click.option(
    "--file",
    "file_path",
    type=click.Path(exists=True, path_type=Path),
    default=DEFAULT_FILE,
    show_default=True,
    help="Markdown file with tasks to sync.",
)
_opt_state = click.option(
    "--state",
    "state_path",
    type=click.Path(path_type=Path),
    default=DEFAULT_STATE,
    show_default=True,
    help="JSON state file tracking synced tasks.",
)
_opt_reminders_list = click.option(
    "--reminders-list",
    default=DEFAULT_REMINDERS_LIST,
    show_default=True,
    help="Target list in Reminders.app.",
)
_opt_notes_folder = click.option(
    "--notes-folder",
    default=DEFAULT_NOTES_FOLDER,
    show_default=True,
    help="Target folder in Notes.app.",
)
_opt_notes_title = click.option(
    "--notes-title",
    default=DEFAULT_NOTES_TITLE,
    show_default=True,
    help="Title of the note in Notes.app.",
)
_opt_dry_run = click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview changes without writing.",
)


def _read_file(file_path: Path) -> str:
    """Read file content with clear error on failure."""
    try:
        return file_path.read_text()
    except OSError as e:
        raise click.ClickException(f"Cannot read {file_path}: {e}") from None


# -- top-level group ---------------------------------------------------------


@click.group()
def main() -> None:
    """Two-way task sync between Markdown, Apple Reminders, and Apple Notes.

    Parses tasks from a ## Tasks section in a markdown file and syncs them
    with Apple Reminders (two-way) and Apple Notes (push-only, native
    checklists via protobuf).
    """


# -- reminders subgroup ------------------------------------------------------


@main.group()
def reminders() -> None:
    """Push/pull tasks to Apple Reminders."""


@reminders.command("push")
@_opt_file
@_opt_state
@_opt_reminders_list
@_opt_dry_run
def reminders_push(
    file_path: Path,
    state_path: Path,
    reminders_list: str,
    dry_run: bool,
) -> None:
    """Push tasks from markdown to Reminders.app."""
    click.echo("Push: markdown -> Reminders")
    content = _read_file(file_path)
    st = state_mod.load(state_path)
    st = push_reminders(content, st, reminders_list, dry_run=dry_run)
    if not dry_run:
        state_mod.save(state_path, st)


@reminders.command("pull")
@_opt_file
@_opt_state
@_opt_reminders_list
@_opt_dry_run
def reminders_pull(
    file_path: Path,
    state_path: Path,
    reminders_list: str,
    dry_run: bool,
) -> None:
    """Pull completion state from Reminders.app into markdown."""
    click.echo("Pull: Reminders -> markdown")
    content = _read_file(file_path)
    st = state_mod.load(state_path)
    content, st = pull(content, st, reminders_list, dry_run=dry_run)
    if not dry_run:
        backup(file_path)
        atomic_write(file_path, content)
        state_mod.save(state_path, st)


# -- notes subgroup ----------------------------------------------------------


@main.group()
def notes() -> None:
    """Push tasks to Apple Notes (one-way)."""


@notes.command("push")
@_opt_file
@_opt_notes_folder
@_opt_notes_title
@_opt_dry_run
def notes_push(
    file_path: Path,
    notes_folder: str,
    notes_title: str,
    dry_run: bool,
) -> None:
    """Push tasks from markdown to Notes.app as native checklists."""
    click.echo("Push: markdown -> Notes")
    content = _read_file(file_path)
    push_notes(content, notes_folder, notes_title, dry_run=dry_run)


# -- top-level commands ------------------------------------------------------


@main.command("sync")
@_opt_file
@_opt_state
@_opt_reminders_list
@_opt_notes_folder
@_opt_notes_title
@_opt_dry_run
def sync_cmd(
    file_path: Path,
    state_path: Path,
    reminders_list: str,
    notes_folder: str,
    notes_title: str,
    dry_run: bool,
) -> None:
    """Full sync: reminders push + notes push + reminders pull."""
    click.echo("Push: markdown -> Reminders")
    content = _read_file(file_path)
    st = state_mod.load(state_path)
    st = push_reminders(content, st, reminders_list, dry_run=dry_run)
    if not dry_run:
        state_mod.save(state_path, st)

    click.echo("Push: markdown -> Notes")
    push_notes(content, notes_folder, notes_title, dry_run=dry_run)

    click.echo("Pull: Reminders -> markdown")
    content = _read_file(file_path)
    content, st = pull(content, st, reminders_list, dry_run=dry_run)
    if not dry_run:
        backup(file_path)
        atomic_write(file_path, content)
        state_mod.save(state_path, st)


@main.command()
@_opt_file
@_opt_state
@_opt_reminders_list
def status(file_path: Path, state_path: Path, reminders_list: str) -> None:
    """Show diff between markdown, state file, and Reminders."""
    content = _read_file(file_path)
    st = state_mod.load(state_path)
    show_status(content, st, reminders_list)


if __name__ == "__main__":
    main()
