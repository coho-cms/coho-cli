"""Printing: tables for people, JSON for scripts, and the shown-once warnings."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable, Sequence
from typing import Any

from rich.console import Console
from rich.table import Table

from ._state import State

console = Console()
err = Console(stderr=True)


def emit_json(data: Any) -> None:
    """Exactly what the contract describes, on stdout."""
    sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")


def table(
    state: State,
    raw: Any,
    columns: Sequence[str],
    rows: Iterable[Sequence[Any]],
    *,
    title: str | None = None,
    empty: str = "(none)",
) -> None:
    """Print ``rows`` as a table, or ``raw`` as JSON when ``--output json``."""
    if state.output == "json":
        emit_json(raw)
        return
    rows = list(rows)
    if not rows:
        console.print(f"[dim]{empty}[/dim]")
        return
    t = Table(title=title, show_lines=False, header_style="bold", box=None, pad_edge=False)
    for c in columns:
        t.add_column(c)
    for r in rows:
        t.add_row(*[_cell(v) for v in r])
    console.print(t)


def record(state: State, raw: Any, pairs: Sequence[tuple[str, Any]]) -> None:
    """One object as ``key  value`` lines, or JSON."""
    if state.output == "json":
        emit_json(raw)
        return
    width = max((len(k) for k, _ in pairs), default=0)
    for k, v in pairs:
        console.print(f"[bold]{k.ljust(width)}[/bold]  {_cell(v)}", highlight=False, markup=True)


def say(state: State, message: str) -> None:
    """A one-line confirmation for humans; silent under ``--output json`` and ``--quiet``."""
    if state.output != "json" and not state.quiet:
        console.print(message, highlight=False)


def warn(message: str) -> None:
    err.print(f"[yellow]warning:[/yellow] {message}", highlight=False)


def secret_once(
    state: State, raw: Any, label: str, value: str, extra: Sequence[tuple[str, Any]] = ()
) -> None:
    """Print a value that the server will never show again.

    In JSON mode the whole response is printed (scripts need the field); in table mode
    the value is printed on its own line, unmarked-up, so it can be copied, with a
    warning on stderr so the warning is never captured into a file.
    """
    if state.output == "json":
        emit_json(raw)
    else:
        for k, v in extra:
            console.print(f"[bold]{k}[/bold]  {_cell(v)}", highlight=False)
        console.print(f"[bold]{label}[/bold]")
        sys.stdout.write(value + "\n")
        sys.stdout.flush()
    err.print(f"[yellow]This {label.lower()} is shown once and cannot be retrieved again.[/yellow]")


def _cell(value: Any) -> str:
    if value is None:
        return "[dim]-[/dim]"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list | tuple):
        return ", ".join(_cell(v) for v in value) if value else "[dim]-[/dim]"
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def short(value: str | None, n: int = 8) -> str:
    return (value or "")[:n]
