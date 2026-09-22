"""ref: list, show, describe — the one namespace of branches, tags and environments."""

from __future__ import annotations

from typing import Annotated

import typer

from .._output import record, table
from .._state import get_state

app = typer.Typer(
    help="Refs: branches, tags and environments share one namespace.", no_args_is_help=True
)


@app.command("list")
def list_(
    ctx: typer.Context,
    kind: Annotated[
        str | None,
        typer.Option("--kind", help="version_branch | feature_branch | tag | environment"),
    ] = None,
) -> None:
    """Every ref in the current project."""
    state = get_state(ctx)
    refs = state.project().refs.list(kind=kind)
    table(
        state,
        {"refs": [r.raw for r in refs]},
        ["REF", "KIND", "TARGET", "DESCRIPTION"],
        [(r.name, r.kind, r.target, r.description) for r in refs],
    )


@app.command("show")
def show(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Argument(help="Default: the current ref.")] = None,
) -> None:
    """One ref. An unset environment is shown with no target."""
    state = get_state(ctx)
    project = state.project()
    r = project.refs.get(name or state.ref().name)
    record(
        state,
        r.raw,
        [("ref", r.name), ("kind", r.kind), ("target", r.target), ("description", r.description)],
    )


@app.command("describe")
def describe(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument()],
    description: Annotated[
        str | None, typer.Argument(help="Omit, or pass --clear, to clear it.")
    ] = None,
    clear: Annotated[bool, typer.Option("--clear")] = False,
) -> None:
    """Set a ref's standing description (release notes on a tag, purpose on a branch)."""
    state = get_state(ctx)
    r = state.project().refs.describe(name, None if clear else description)
    record(state, r.raw, [("ref", r.name), ("kind", r.kind), ("description", r.description)])
