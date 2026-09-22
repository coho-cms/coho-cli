"""member: list, role, remove, leave."""

from __future__ import annotations

from typing import Annotated

import typer

from coho_sdk.models import ACCOUNT_ROLES

from .._output import record, say, table
from .._state import State, Usage, get_state

app = typer.Typer(
    help="Account members and their account-level role (admin/member).", no_args_is_help=True
)


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """The account's members (admin)."""
    state = get_state(ctx)
    members = state.account().members.list()
    table(
        state,
        {"users": [u.raw for u in members]},
        ["USER", "NAME", "EMAIL", "ROLE"],
        [(u.id, u.display_name, u.email, u.role) for u in members],
    )


@app.command("role")
def role(
    ctx: typer.Context,
    user: Annotated[str, typer.Argument(help="User id, or an email of a current member.")],
    role: Annotated[str, typer.Argument(help="`admin` or `member`.")],
) -> None:
    """Change a member's account role (admin). Refused if it would leave no admin."""
    state = get_state(ctx)
    if role not in ACCOUNT_ROLES:
        raise Usage(f"role must be one of: {', '.join(ACCOUNT_ROLES)}")
    acct = state.account()
    member = acct.members.change_role(_resolve_user(state, user), role)
    record(state, member.raw, [("user", member.id), ("email", member.email), ("role", member.role)])


@app.command("remove")
def remove(
    ctx: typer.Context,
    user: Annotated[str, typer.Argument(help="User id, or an email of a current member.")],
) -> None:
    """Remove a member from the account (admin)."""
    state = get_state(ctx)
    acct = state.account()
    user_id = _resolve_user(state, user)
    if not state.yes and not typer.confirm(f"Remove {user} from {acct.name or acct.id}?"):
        raise typer.Abort()
    acct.members.remove(user_id)
    say(state, f"Removed {user}.")


@app.command("leave")
def leave(ctx: typer.Context) -> None:
    """Leave the current account yourself."""
    state = get_state(ctx)
    acct = state.account()
    me = state.coho.me()
    if not state.yes and not typer.confirm(f"Leave {acct.name or acct.id}?"):
        raise typer.Abort()
    acct.members.remove(me.user_id)
    say(state, f"Left {acct.name or acct.id}.")


def _resolve_user(state: State, value: str) -> str:
    if "@" not in value:
        return value
    for u in state.account().members.list():
        if (u.email or "").lower() == value.lower():
            return u.id
    raise Usage(f"no member with email {value}")
