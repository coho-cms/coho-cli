"""key: create, list, revoke, public — delivery keys (owner)."""

from __future__ import annotations

from typing import Annotated

import typer

from .._output import console, say, secret_once, table
from .._state import get_state

app = typer.Typer(
    help="Delivery keys: what a website presents to read published content.", no_args_is_help=True
)


@app.command("create")
def create(
    ctx: typer.Context,
    label: Annotated[
        str | None, typer.Option("--label", "-l", help="What this key is for.")
    ] = None,
    refs: Annotated[
        list[str] | None,
        typer.Option("--ref", "-r", help="Limit to these refs (repeatable). Default: every ref."),
    ] = None,
    expires_in_days: Annotated[
        int | None, typer.Option("--expires-in-days", help="1..3650")
    ] = None,
) -> None:
    """Issue a delivery key. ⚠️ Shown once; only its hash is stored."""
    state = get_state(ctx)
    issued = state.project().delivery_keys.issue(
        label=label, refs=refs or None, expires_in_days=expires_in_days
    )
    d = issued.delivery
    secret_once(
        state,
        issued.raw,
        "Delivery key",
        issued.key,
        extra=[
            ("id", d.id),
            ("label", d.label),
            ("refs", d.refs or "(all)"),
            ("expires", d.expires_at),
        ],
    )


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """Keys (metadata only) and the refs readable without one."""
    state = get_state(ctx)
    ks = state.project().delivery_keys.list()
    table(
        state,
        ks.raw,
        ["KEY", "LABEL", "REFS", "CREATED", "EXPIRES"],
        [(k.id, k.label, k.refs or "(all)", k.created_at, k.expires_at) for k in ks.keys],
        empty="(no keys)",
    )
    if state.output != "json":
        console.print(f"\npublic refs: {', '.join(ks.public_refs) or '(none)'}")


@app.command("revoke")
def revoke(ctx: typer.Context, key_id: Annotated[str, typer.Argument()]) -> None:
    """Revoke a key. Delivery stops accepting it within a few seconds."""
    state = get_state(ctx)
    if not state.yes and not typer.confirm(f"Revoke key {key_id}?"):
        raise typer.Abort()
    state.project().delivery_keys.revoke(key_id)
    say(state, f"Revoked {key_id}.")


@app.command("public")
def public(
    ctx: typer.Context,
    refs: Annotated[
        list[str] | None, typer.Argument(help="Environment names. None clears.")
    ] = None,
) -> None:
    """Set which environments are readable without a key. Replaces the whole set."""
    state = get_state(ctx)
    ks = state.project().delivery_keys.set_public(refs or [])
    if state.output == "json":
        from .._output import emit_json

        emit_json(ks.raw)
    else:
        say(state, f"public refs: {', '.join(ks.public_refs) or '(none)'}")
