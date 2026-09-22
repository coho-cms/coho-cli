"""account: list, show, rename, entitlements, events, plans."""

from __future__ import annotations

from typing import Annotated

import typer

from .._output import record, table
from .._state import get_state

app = typer.Typer(help="Accounts you belong to.", no_args_is_help=True)


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """Accounts the signed-in user belongs to (from /api/v1/me)."""
    state = get_state(ctx)
    me = state.coho.me()
    table(
        state,
        me.raw.get("accounts", []),
        ["ACCOUNT", "ID", "ROLE", "ACTOR"],
        [(a.account_name, a.account_id, a.role, a.actor_id) for a in me.accounts],
        empty="(no accounts)",
    )


@app.command("show")
def show(ctx: typer.Context, account: Annotated[str | None, typer.Argument()] = None) -> None:
    """One account, with your role and its entitlements."""
    state = get_state(ctx)
    acct = state.coho.account(account) if account else state.account()
    ent = acct.entitlements() if acct.role == "admin" else None
    raw = {"account": acct.membership.raw if acct.membership else {"accountId": acct.id}}
    if ent:
        raw["entitlements"] = ent.raw
    record(
        state,
        raw,
        [
            ("id", acct.id),
            ("name", acct.name),
            ("your role", acct.role),
            ("plan", ent.plan if ent else "(admin only)"),
            ("max projects", _limit(ent.max_projects) if ent else None),
            ("max live envs", _limit(ent.max_live_environments) if ent else None),
            ("max members", _limit(ent.max_members) if ent else None),
        ],
    )


@app.command("rename")
def rename(ctx: typer.Context, name: Annotated[str, typer.Argument(help="The new name.")]) -> None:
    """Rename the current account (admin)."""
    state = get_state(ctx)
    info = state.account().rename(name)
    record(
        state,
        info.raw,
        [("id", info.id), ("name", info.name), ("status", info.status), ("plan", info.plan)],
    )


@app.command("entitlements")
def entitlements(ctx: typer.Context) -> None:
    """What the account's plan allows (admin). An absent limit is unlimited."""
    state = get_state(ctx)
    ent = state.account().entitlements()
    record(
        state,
        ent.raw,
        [
            ("plan", ent.plan),
            ("plan status", ent.plan_status),
            ("max projects", _limit(ent.max_projects)),
            ("max live envs", _limit(ent.max_live_environments)),
            ("max members", _limit(ent.max_members)),
        ],
    )


@app.command("events")
def events(
    ctx: typer.Context, limit: Annotated[int, typer.Option("--limit", help="1..200")] = 50
) -> None:
    """The account's audit trail, newest first (admin)."""
    state = get_state(ctx)
    evs = state.account().events(limit=limit)
    table(
        state,
        {"events": [e.raw for e in evs]},
        ["AT", "ACTION", "BY", "SUBJECT", "DETAIL"],
        [
            (
                e.created_at,
                e.action,
                "operator" if e.by_operator else (e.by_user_id or "(erased user)"),
                e.subject_user_id or e.subject_id,
                e.detail or None,
            )
            for e in evs
        ],
    )


@app.command("plans")
def plans(
    ctx: typer.Context, include_retired: Annotated[bool, typer.Option("--include-retired")] = False
) -> None:
    """The plan catalogue."""
    state = get_state(ctx)
    ps = state.coho.plans(include_retired=include_retired)
    table(
        state,
        {"plans": [p.raw for p in ps]},
        ["PLAN", "STATUS", "PROJECTS", "LIVE ENVS", "MEMBERS"],
        [
            (
                p.id,
                p.status,
                _limit(p.max_projects),
                _limit(p.max_live_environments),
                _limit(p.max_members),
            )
            for p in ps
        ],
    )


def _limit(value: int | None) -> str:
    return "unlimited" if value is None else str(value)
