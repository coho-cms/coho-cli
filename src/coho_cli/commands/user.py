"""user: rename, logins, detach-login — acting on yourself."""

from __future__ import annotations

from typing import Annotated

import typer

from .._output import record, say, table
from .._state import get_state

app = typer.Typer(help="Your own user: display name and attached identities.", no_args_is_help=True)


@app.command("rename")
def rename(ctx: typer.Context, display_name: Annotated[str, typer.Argument()]) -> None:
    """Change your display name."""
    state = get_state(ctx)
    me = state.coho.me()
    updated = state.coho.users.rename(me.user_id, display_name)
    record(
        state,
        updated.raw,
        [("user", updated.user_id), ("name", updated.display_name), ("email", updated.email)],
    )


@app.command("logins")
def logins(ctx: typer.Context) -> None:
    """Identities attached to you."""
    state = get_state(ctx)
    me = state.coho.me()
    ls = state.coho.users.logins(me.user_id)
    table(
        state,
        {"logins": [x.raw for x in ls]},
        ["LOGIN", "PROVIDER", "SUBJECT"],
        [(x.id, x.provider, x.subject) for x in ls],
    )


@app.command("detach-login")
def detach_login(ctx: typer.Context, login_id: Annotated[str, typer.Argument()]) -> None:
    """Detach an identity. Refused if it is your only one."""
    state = get_state(ctx)
    me = state.coho.me()
    if not state.yes and not typer.confirm(f"Detach login {login_id}?"):
        raise typer.Abort()
    state.coho.users.detach_login(me.user_id, login_id)
    say(state, f"Detached {login_id}.")
