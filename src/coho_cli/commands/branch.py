"""branch: list, create, delete."""

from __future__ import annotations

from typing import Annotated

import typer
from coho_management_sdk.errors import BranchNotMerged

from .._output import record, say, table, warn
from .._state import State, get_state
from .context import save_ref

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
        [
            (
                b.name,
                b.kind,
                # `open` after a merge is another fact from `open` never merged. `-o json` keeps
                # both as the API says them.
                "changed" if b.changed_since_merge else b.status,
                b.parent,
                b.depth,
                b.pending_forward_port,
            )
            for b in branches
        ],
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
    use: Annotated[bool, typer.Option("--use/--no-use", help="Make it the current ref.")] = True,
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
        save_ref(state, b.name)


@app.command("delete")
def delete(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument()],
    confirm_destructive: Annotated[
        bool,
        typer.Option(
            "--confirm-destructive",
            help="Delete it even if it may hold work merged nowhere. Needed with --yes.",
        ),
    ] = False,
) -> None:
    """Delete a branch. Its name is free again, and an owner can restore it.

    Refused for the trunk, and for a branch with branches cut from it, tags on it, or an
    environment pointing at it. See `coho ref restore`.
    """
    state = get_state(ctx)
    if not state.yes and not typer.confirm(f"Delete branch {name}? An owner can restore it."):
        raise typer.Abort()
    branches = state.project().branches
    try:
        branches.delete(name, confirm_destructive=confirm_destructive)
    except BranchNotMerged:
        # Asked here, not up front: a merged branch discards nothing, so needs no second question.
        if state.yes or not typer.confirm(
            f"{name} has not been merged, so work on it may be nowhere else. Delete it anyway?"
        ):
            raise
        branches.delete(name, confirm_destructive=True)
    say(state, f"Deleted branch {name}.")
    _forget_if_current(state, name)


def _forget_if_current(state: State, name: str) -> None:
    """A saved ref naming a deleted branch would fail every command after this one."""
    if state.profile.context.ref == name:
        state.profile.context.ref = None
        state.save()
        say(state, "It was the current ref, so none is set now. Choose one: `coho ref switch`.")
