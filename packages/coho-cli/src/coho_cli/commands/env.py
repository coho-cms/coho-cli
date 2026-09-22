"""env: list, show, create, promote, unset, delete, history; promote; rollback."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.status import Status

from coho_sdk.errors import SnapshotNotReady
from coho_sdk.models import Environment

from .._output import console, record, say, table, warn
from .._state import State, get_state

app = typer.Typer(
    help="Environments: the refs that move. Promote, roll back, unset.", no_args_is_help=True
)


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """Environments in pipeline order."""
    state = get_state(ctx)
    envs = state.project().environments.list()
    table(
        state,
        {"environments": [e.raw for e in envs]},
        ["ENVIRONMENT", "TIER", "RESOLVES", "TARGET"],
        [(e.name, e.tier, e.resolves, e.target or "(unset)") for e in envs],
    )


@app.command("show")
def show(ctx: typer.Context, name: Annotated[str, typer.Argument()]) -> None:
    """One environment."""
    state = get_state(ctx)
    e = state.project().environments.get(name)
    record(
        state,
        e.raw,
        [("environment", e.name), ("tier", e.tier), ("resolves", e.resolves), ("target", e.target)],
    )


@app.command("create")
def create(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument()],
    tier: Annotated[str, typer.Option("--tier", help="Fixed at creation. Needs promote:<tier>.")],
    target: Annotated[str | None, typer.Option("--target", help="Optional initial target.")] = None,
) -> None:
    """Create an environment in a tier."""
    state = get_state(ctx)
    e = state.project().environments.create(name, tier=tier, target=target)
    record(state, e.raw, [("environment", e.name), ("tier", e.tier), ("target", e.target)])


def promote(
    ctx: typer.Context,
    environment: Annotated[str, typer.Argument(help="e.g. qa, stage, prod")],
    target: Annotated[str, typer.Argument(help="A tag (snapshot tier) or a branch (live tier).")],
    expected: Annotated[
        str | None,
        typer.Option(
            "--expected", help="Only if it currently points here (else ENVIRONMENT_MOVED)."
        ),
    ] = None,
    reason: Annotated[
        str | None, typer.Option("--reason", "-m", help="Recorded in the history.")
    ] = None,
    wait: Annotated[
        bool, typer.Option("--wait/--no-wait", help="Wait for the snapshot to be ready.")
    ] = True,
    timeout: Annotated[int, typer.Option("--timeout", help="Seconds to wait.")] = 300,
) -> None:
    """Repoint an environment at a tag or branch. Waits on SNAPSHOT_NOT_READY by default."""
    state = get_state(ctx)
    api = state.project().environments
    status: Status | None = None

    def on_wait(exc: SnapshotNotReady, remaining: float) -> None:
        nonlocal status
        if state.output == "json" or state.quiet:
            return
        if status is None:
            status = Status("snapshot not ready; waiting…", console=console)
            status.start()
        status.update(
            f"snapshot for {target} not ready ({exc.context.get('state', '…')}); "
            f"{int(remaining)}s left"
        )

    try:
        e = api.promote(
            environment,
            target,
            expected_target=expected,
            reason=reason,
            wait=wait,
            timeout=timeout,
            on_wait=on_wait,
        )
    finally:
        if status is not None:
            status.stop()
    _repointed(state, e)


def rollback(
    ctx: typer.Context,
    environment: Annotated[str, typer.Argument()],
    reason: Annotated[str | None, typer.Option("--reason", "-m")] = None,
    wait: Annotated[bool, typer.Option("--wait/--no-wait")] = True,
) -> None:
    """Repoint an environment at its previous target, only if nobody moved it since.

    There is no rollback endpoint by design: this reads the history and issues the
    same repoint as `promote`, with --expected set to the current target.
    """
    state = get_state(ctx)
    api = state.project().environments
    hist = api.history(environment, limit=10)
    entries = [h for h in hist.history if h.to_target is not None]
    if len(entries) >= 2 and not state.yes and state.output != "json":
        console.print(f"{environment}: {entries[0].to_target} → {entries[1].to_target}")
        if not typer.confirm("Roll back?"):
            raise typer.Abort()
    e = api.rollback(environment, reason=reason, wait=wait)
    _repointed(state, e)


@app.command("unset")
def unset(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument()],
    reason: Annotated[str | None, typer.Option("--reason", "-m")] = None,
) -> None:
    """Point an environment at nothing."""
    state = get_state(ctx)
    e = state.project().environments.unset(name, reason=reason)
    _repointed(state, e)


@app.command("delete")
def delete(ctx: typer.Context, name: Annotated[str, typer.Argument()]) -> None:
    """Remove an environment. Auditable: the removal stays in its history."""
    state = get_state(ctx)
    if not state.yes and not typer.confirm(f"Delete environment {name}?"):
        raise typer.Abort()
    state.project().environments.delete(name)
    say(state, f"Deleted environment {name}.")


@app.command("history")
def history(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument()],
    limit: Annotated[int, typer.Option("--limit")] = 20,
    offset: Annotated[int, typer.Option("--offset")] = 0,
) -> None:
    """Where the environment has pointed, newest first. What rollback reads."""
    state = get_state(ctx)
    h = state.project().environments.history(name, limit=limit, offset=offset)
    table(
        state,
        h.raw,
        ["AT", "FROM", "TO", "REASON", "ACTOR"],
        [(x.at, x.from_target, x.to_target or "(unset)", x.reason, x.actor) for x in h.history],
    )


app.command("promote")(promote)
app.command("rollback")(rollback)


def _repointed(state: State, e: Environment) -> None:
    record(
        state,
        e.raw,
        [
            ("environment", e.name),
            ("tier", e.tier),
            ("target", e.target),
            ("previous", e.previous_target),
        ],
    )
    for w in e.warnings:
        warn(f"{w.code}: {w.message}")
