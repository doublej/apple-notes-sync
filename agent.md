# Agent Guidelines

See [CLAUDE.md](CLAUDE.md) for stack, project structure, conventions, and CLI commands.

## Verify Loop

Run `just check` after every change (loc-check + lint + format-check + typecheck + test).

To auto-fix before checking: `just fix` (lint + format), then `just check`.

### Auto-fixable

- `uv run ruff check --fix src/ tests/` — auto-fix lint issues
- `uv run ruff format src/ tests/` — format code

### Common Tasks

- Add a Click command: define a function decorated with `@main.command()` in `cli.py`
- Add a command group: use `@click.group()` and register subcommands
- Add a subcommand module: create a new file in the package, import and register in `cli.py`
- Add a dependency: `uv add <package>`

### Testing

- Test files: `tests/test_*.py`
- Use `click.testing.CliRunner` for CLI tests
- Run a single test: `uv run pytest tests/test_foo.py::test_name -v`

### Boundaries

- Do not deploy, publish, or push
- Do not modify `[tool.*]` sections in `pyproject.toml` without asking
