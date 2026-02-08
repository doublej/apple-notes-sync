import click


@click.group()
def main():
    """Two-way task sync between Markdown, Apple Reminders, and Apple Notes with native checklists"""
    pass


@main.command()
def hello():
    """Say hello."""
    click.echo("Hello from Apple Notes Sync!")


if __name__ == "__main__":
    main()
