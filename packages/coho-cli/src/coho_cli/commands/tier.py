"""tier: list, create, delete — the promotion pipeline (owner)."""

from __future__ import annotations

from typing import Annotated

import typer

from .._output import record, say, table
from .._state import Usage, get_state

app = typer.Typer(
    help="Tiers: the promotion pipeline, and the grant that guards each step.", no_args_is_help=True
)


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """Tiers in order, with the environments in each."""
    state = get_state(ctx)
    tiers = state.project().tiers.list()
    table(
        state,
        {"tiers": [t.raw for t in tiers]},
        ["ORD", "TIER", "RESOLVES", "PERMISSION", "ENVIRONMENTS"],
        [
            (t.ord, t.id, t.resolves, t.promote_permission, t.environments)
            for t in sorted(tiers, key=lambda t: t.ord)
        ],
    )


@app.command("create")
def create(
    ctx: typer.Context,
    tier_id: Annotated[str, typer.Argument()],
    resolves: Annotated[
        str,
        typer.Option("--resolves", help="`live` (branch tips) or `snapshot` (tags). Immutable."),
    ],
    ord_: Annotated[int, typer.Option("--ord", help="Display order; advisory.")],
) -> None:
    """Define a tier (owner)."""
    state = get_state(ctx)
    if resolves not in ("live", "snapshot"):
        raise Usage("--resolves must be `live` or `snapshot`")
    t = state.project().tiers.create(tier_id, resolves=resolves, ord=ord_)
    record(
        state,
        t.raw,
        [
            ("tier", t.id),
            ("resolves", t.resolves),
            ("ord", t.ord),
            ("permission", t.promote_permission),
        ],
    )


@app.command("delete")
def delete(ctx: typer.Context, tier_id: Annotated[str, typer.Argument()]) -> None:
    """Remove an empty tier (owner)."""
    state = get_state(ctx)
    state.project().tiers.delete(tier_id)
    say(state, f"Deleted tier {tier_id}.")
