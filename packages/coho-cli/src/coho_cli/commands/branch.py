"""branch: list, create."""

from __future__ import annotations

from typing import Annotated

import typer

from .._output import record, say, table, warn
from .._state import get_state

app = typer.Typer(help="Branches. Creating one is O(1) and copies nothing.", no_args_is_help=True)


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """Every branch, with depth and status."""
    state = get_state(ctx)
    branches = state.project().branches.list()
    table(
        state,
        {"branches": [b.raw for b in branches]},
        ["BRANCH", "KIND", "STATUS", "PARENT", "DEPTH", "PENDING FWD-PORT"],
        [(b.name, b.kind, b.status, b.parent, b.depth, b.pending_forward_port) for b in branches],
    )


@app.command("create")
def create(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="e.g. feature/pricing")],
    from_ref: Annotated[
        str | None, typer.Option("--from", help="A branch tip or a tag. Default: the current ref.")
    ] = None,
    version: Annotated[
        bool, typer.Option("--version", help="Cut a version branch (needs branch:create_version).")
    ] = False,
    description: Annotated[str | None, typer.Option("--description", "-m")] = None,
    at: Annotated[
        int | None, typer.Option("--at", help="Branch at an explicit sequence, not a timestamp.")
    ] = None,
    use: Annotated[
        bool, typer.Option("--use/--no-use", help="Switch the context ref to it.")
    ] = False,
) -> None:
    """Create a feature branch (or a version branch with --version)."""
    state = get_state(ctx)
    project = state.project()
    source = from_ref or state.context.ref
    if not source:
        from .._state import Usage

        raise Usage("--from is required when no ref is in context")
    b = project.branches.create(
        name,
        from_ref=source,
        kind="version_branch" if version else "feature_branch",
        description=description,
        at=at,
    )
    record(
        state,
        b.raw,
        [
            ("branch", b.name),
            ("kind", b.kind),
            ("from", b.parent),
            ("branched at", b.branched_at),
            ("depth", b.depth),
        ],
    )
    if b.depth_warning:
        warn("this branch is deep; resolution gets slower with depth")
    if use:
        state.profile.context.ref = b.name
        state.save()
        say(state, f"Context ref is now [bold]{b.name}[/bold].")
