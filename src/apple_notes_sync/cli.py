"""Click CLI entry point for apple-notes-sync."""

from pathlib import Path

import click

from apple_notes_sync import state as state_mod
from apple_notes_sync.sync import pull, push, show_status

DEFAULT_FILE = Path("Now/Current Focus.md")
DEFAULT_STATE = Path(".tasks-sync.json")
DEFAULT_REMINDERS_LIST = "Current Focus"
DEFAULT_NOTES_FOLDER = "Current Focus"
DEFAULT_NOTES_TITLE = "Tasks"


def _common_options(fn: click.decorators.FC) -> click.decorators.FC:
    """Shared CLI options for all sync commands."""
    fn = click.option("--file", "file_path", type=click.Path(exists=True, path_type=Path), default=DEFAULT_FILE, help="Markdown file to sync.")(fn)
    fn = click.option("--state", "state_path", type=click.Path(path_type=Path), default=DEFAULT_STATE, help="State file location.")(fn)
    fn = click.option("--reminders-list", default=DEFAULT_REMINDERS_LIST, help="Reminders list name.")(fn)
    fn = click.option("--notes-folder", default=DEFAULT_NOTES_FOLDER, help="Notes folder name.")(fn)
    fn = click.option("--notes-title", default=DEFAULT_NOTES_TITLE, help="Notes note title.")(fn)
    return fn


@click.group()
def main() -> None:
    """Two-way task sync between Markdown, Apple Reminders, and Apple Notes."""


@main.command("push")
@_common_options
def push_cmd(
    file_path: Path,
    state_path: Path,
    reminders_list: str,
    notes_folder: str,
    notes_title: str,
) -> None:
    """Push markdown tasks to Reminders + Notes."""
    click.echo("Push: markdown -> Reminders + Notes")
    content = file_path.read_text()
    st = state_mod.load(state_path)
    st = push(content, st, reminders_list, notes_folder, notes_title)
    state_mod.save(state_path, st)


@main.command("pull")
@_common_options
def pull_cmd(
    file_path: Path,
    state_path: Path,
    reminders_list: str,
    notes_folder: str,
    notes_title: str,
) -> None:
    """Pull Reminders state into markdown."""
    click.echo("Pull: Reminders -> markdown")
    content = file_path.read_text()
    st = state_mod.load(state_path)
    content, st = pull(content, st, reminders_list)
    file_path.write_text(content)
    state_mod.save(state_path, st)


@main.command("sync")
@_common_options
def sync_cmd(
    file_path: Path,
    state_path: Path,
    reminders_list: str,
    notes_folder: str,
    notes_title: str,
) -> None:
    """Full two-way sync (push then pull)."""
    click.echo("Push: markdown -> Reminders + Notes")
    content = file_path.read_text()
    st = state_mod.load(state_path)
    st = push(content, st, reminders_list, notes_folder, notes_title)
    state_mod.save(state_path, st)

    click.echo("Pull: Reminders -> markdown")
    content = file_path.read_text()
    content, st = pull(content, st, reminders_list)
    file_path.write_text(content)
    state_mod.save(state_path, st)


@main.command()
@_common_options
def status(
    file_path: Path,
    state_path: Path,
    reminders_list: str,
    notes_folder: str,
    notes_title: str,
) -> None:
    """Show sync state diff."""
    content = file_path.read_text()
    st = state_mod.load(state_path)
    show_status(content, st, reminders_list)


if __name__ == "__main__":
    main()
