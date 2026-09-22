"""role: list, grant, revoke — project roles."""

from __future__ import annotations

from typing import Annotated

import typer

from coho_sdk.models import PROJECT_ROLES

from .._output import console, record, say, table
from .._state import State, Usage, get_state

app = typer.Typer(
    help="Project roles: viewer, author, maintainer, release_manager, owner.", no_args_is_help=True
)


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """Who holds what in the current project (owner). Ids, never names; join with `member list`."""
    state = get_state(ctx)
    roles = state.project().roles.list()
    actors = _actor_names(state)
    table(
        state,
        {"roles": [r.raw for r in roles]},
        ["ACTOR", "WHO", "ROLE", "GRANTED BY", "GRANTED AT"],
        [(r.actor_id, actors.get(r.actor_id), r.role, r.granted_by, r.granted_at) for r in roles],
    )
    if state.output != "json":
        console.print(
            "[dim]WHO is filled in for you only; the content tier stores ids, not names.[/dim]"
        )


@app.command("grant")
def grant(
    ctx: typer.Context,
    actor: Annotated[str, typer.Argument(help="Actor id (see `coho account list`), or `me`.")],
    role: Annotated[str, typer.Argument(help="One of: " + ", ".join(PROJECT_ROLES))],
) -> None:
    """Grant or change a role (owner). Repeating it changes the role; it never stacks."""
    state = get_state(ctx)
    if role not in PROJECT_ROLES:
        raise Usage(f"role must be one of: {', '.join(PROJECT_ROLES)}")
    r = state.project().roles.grant(_resolve_actor(state, actor), role)
    record(
        state,
        r.raw,
        [
            ("actor", r.actor_id),
            ("role", r.role),
            ("granted by", r.granted_by),
            ("granted at", r.granted_at),
        ],
    )


@app.command("revoke")
def revoke(
    ctx: typer.Context, actor: Annotated[str, typer.Argument(help="Actor id, or `me`.")]
) -> None:
    """Revoke this project's grant. An account admin keeps implied owner."""
    state = get_state(ctx)
    state.project().roles.revoke(_resolve_actor(state, actor))
    say(state, f"Revoked {actor}.")


@app.command("ladder")
def ladder(ctx: typer.Context) -> None:
    """What each role may do."""
    state = get_state(ctx)
    rows = [
        ("viewer", "content:read"),
        ("author", "+ content:write, branch:create"),
        ("maintainer", "+ merge, release:tag, promote:dev, promote:qa"),
        ("release_manager", "+ promote:stage, promote:prod, branch:create_version"),
        ("owner", "all, including role:grant, delivery:keys, workflow:write"),
    ]
    table(state, [{"role": r, "permissions": p} for r, p in rows], ["ROLE", "PERMISSIONS"], rows)


def _actor_names(state: State) -> dict[str, str]:
    me = state.coho.me()
    return {a.actor_id: f"{me.display_name or me.email} (you)" for a in me.accounts if a.actor_id}


def _resolve_actor(state: State, actor: str) -> str:
    if actor != "me":
        return actor
    acct = state.account()
    membership = state.coho.me(refresh=True).membership(acct.id)
    if membership is None or not membership.actor_id:
        raise Usage("you have no actor in this account yet; run any content command first")
    return str(membership.actor_id)
