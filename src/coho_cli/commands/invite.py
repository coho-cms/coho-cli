"""invite: create, list, revoke, lookup, accept."""

from __future__ import annotations

from typing import Annotated

import typer
from coho_management_sdk.models import ACCOUNT_ROLES

from .._output import console, record, say, secret_once, table
from .._state import Usage, get_state

app = typer.Typer(help="Invitations into an account.", no_args_is_help=True)


@app.command("create")
def create(
    ctx: typer.Context,
    email: Annotated[str, typer.Argument()],
    role: Annotated[str, typer.Option("--role", help="`member` (default) or `admin`.")] = "member",
    link: Annotated[
        bool, typer.Option("--link/--token", help="Print a link (default) or the bare token.")
    ] = True,
) -> None:
    """Invite somebody by email (admin). ⚠️ The token is shown once.

    Coho does not send the email. Deliver the link yourself, over a channel that does
    not leak: the token rides in the URL fragment, which browsers never send to servers.
    """
    state = get_state(ctx)
    if role not in ACCOUNT_ROLES:
        raise Usage(f"--role must be one of: {', '.join(ACCOUNT_ROLES)}")
    issued = state.account().invitations.create(email, role=role)
    inv = issued.invitation
    url = state.config.effective_url(state.profile)
    value = issued.link(url) if link and url else issued.token
    secret_once(
        state,
        issued.raw,
        "Invitation link" if link and url else "Invitation token",
        value,
        extra=[
            ("invitation", inv.id),
            ("email", inv.email),
            ("role", inv.role),
            ("expires", inv.expires_at),
        ],
    )


@app.command("list")
def list_(
    ctx: typer.Context,
    all_: Annotated[bool, typer.Option("--all", help="Include non-pending.")] = False,
) -> None:
    """Outstanding invitations (admin)."""
    state = get_state(ctx)
    invs = state.account().invitations.list()
    if not all_:
        invs = [i for i in invs if i.status == "pending"]
    table(
        state,
        {"invitations": [i.raw for i in invs]},
        ["INVITATION", "EMAIL", "ROLE", "STATUS", "EXPIRES"],
        [(i.id, i.email, i.role, i.status, i.expires_at) for i in invs],
        empty="(no pending invitations)",
    )


@app.command("revoke")
def revoke(
    ctx: typer.Context,
    invitation: Annotated[str, typer.Argument(help="Invitation id, or the invited email.")],
) -> None:
    """Revoke a pending invitation (admin)."""
    state = get_state(ctx)
    acct = state.account()
    inv_id = invitation
    if "@" in invitation:
        matches = [
            i
            for i in acct.invitations.list()
            if i.email.lower() == invitation.lower() and i.status == "pending"
        ]
        if not matches:
            raise Usage(f"no pending invitation for {invitation}")
        inv_id = matches[0].id
    acct.invitations.revoke(inv_id)
    say(state, f"Revoked invitation {inv_id}.")


@app.command("lookup")
def lookup(
    ctx: typer.Context,
    token: Annotated[str, typer.Argument(help="The token from an invitation link.")],
) -> None:
    """What an invitation offers, before accepting it. Needs no login."""
    state = get_state(ctx)
    inv = state.coho.invitation_lookup(_strip_fragment(token))
    record(
        state,
        inv.raw,
        [
            ("account", inv.account_name),
            ("email", inv.email),
            ("role", inv.role),
            ("status", inv.status),
            ("expires", inv.expires_at),
        ],
    )


@app.command("accept")
def accept(
    ctx: typer.Context,
    token: Annotated[str, typer.Argument(help="The token (or the whole link).")],
    display_name: Annotated[
        str | None, typer.Option("--name", help="Your display name, if new here.")
    ] = None,
    no_browser: Annotated[bool, typer.Option("--no-browser")] = False,
) -> None:
    """Accept an invitation. Finishes in the browser; then run `coho login`."""
    import webbrowser

    state = get_state(ctx)
    url = state.coho.invitation_accept_start(_strip_fragment(token), display_name=display_name)
    if no_browser:
        console.print(url, markup=False, highlight=False, soft_wrap=True)
    else:
        webbrowser.open(url)
        say(state, "Opened the acceptance page. When it says you are signed in, run `coho login`.")


def _strip_fragment(value: str) -> str:
    return value.rsplit("#", 1)[-1] if "#" in value else value
