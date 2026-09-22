"""tag: list, create."""

from __future__ import annotations

from typing import Annotated

import typer

from .._output import record, table, warn
from .._state import get_state

app = typer.Typer(
    help="Tags: immutable, undeletable (branch, seq) coordinates.", no_args_is_help=True
)


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """Every tag, with its release notes."""
    state = get_state(ctx)
    tags = state.project().tags.list()
    table(
        state,
        {"refs": [t.raw for t in tags]},
        ["TAG", "TARGET", "DESCRIPTION"],
        [(t.name, t.target, t.description) for t in tags],
    )


@app.command("create")
def create(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Any non-blank name ≤255 chars, e.g. v1.4.0")],
    branch: Annotated[
        str | None,
        typer.Option("--branch", help="The version branch to tag. Default: the current ref."),
    ] = None,
    description: Annotated[
        str | None, typer.Option("--description", "-m", help="Release notes.")
    ] = None,
    at: Annotated[
        int | None,
        typer.Option("--at", help="Tag at an explicit sequence (default: the high-water mark)."),
    ] = None,
) -> None:
    """Cut a tag on a version branch. Does not merge and does not validate."""
    state = get_state(ctx)
    source = branch or state.context.ref
    if not source:
        from .._state import Usage

        raise Usage("--branch is required when no ref is in context")
    t = state.project().tags.create(name, branch=source, description=description, at=at)
    record(state, t.raw, [("tag", t.name), ("branch", t.ref), ("at", t.at)])
    for w in t.warnings:
        warn(f"{w.code}: {w.message}")
