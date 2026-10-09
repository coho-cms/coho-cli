"""token: create, list, revoke — project tokens for automation (owner).

A project token (``coho_pt_…``) holds one role in one project, below owner. Hand it to
CI as ``COHO_TOKEN``; it is refused everywhere but that project's content, so a job
using it must name the account by id (``--account`` or ``COHO_ACCOUNT``).
"""

from __future__ import annotations

from typing import Annotated

import typer
from coho_management_sdk.client import ProjectTokensApi

from .._output import say, secret_once, table
from .._state import Usage, get_state

app = typer.Typer(
    help="Project tokens: credentials for automation, one role in one project.",
    no_args_is_help=True,
)


@app.command("create")
def create(
    ctx: typer.Context,
    role: Annotated[
        str,
        typer.Option("--role", "-r", help="viewer, author, maintainer or release_manager."),
    ],
    label: Annotated[
        str, typer.Option("--label", "-l", help="What it is for, e.g. GitHub Actions.")
    ],
    expires_in_days: Annotated[
        int | None,
        typer.Option("--expires", help="Days until it stops working: 1..365, default 90."),
    ] = None,
) -> None:
    """Create a token for the current project. ⚠️ Shown once; only its hash is stored."""
    if role not in ProjectTokensApi.ROLES:
        raise Usage(
            f"--role must be one of {', '.join(ProjectTokensApi.ROLES)}; "
            "a token can never be an owner"
        )
    state = get_state(ctx)
    created = state.project().tokens.create(label, role, expires_in_days=expires_in_days)
    t = created.project_token
    secret_once(
        state,
        created.raw,
        "Project token",
        created.token,
        extra=[("id", t.id), ("label", t.label), ("role", t.role), ("expires", t.expires_at)],
    )
    say(
        state, "Give it to automation as COHO_TOKEN, with COHO_ACCOUNT and COHO_PROJECT set to ids."
    )


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """The project's tokens, revoked and expired ones included (their ids are in the history)."""
    state = get_state(ctx)
    tokens = state.project().tokens.list()
    table(
        state,
        {"tokens": [t.raw for t in tokens]},
        ["TOKEN", "LABEL", "ROLE", "STATE", "EXPIRES", "LAST USED"],
        [(t.id, t.label, t.role, t.state, t.expires_at, t.last_used_at or "never") for t in tokens],
        empty="(no tokens)",
    )


@app.command("revoke")
def revoke(ctx: typer.Context, token_id: Annotated[str, typer.Argument()]) -> None:
    """Revoke a token. It stops working on its next request."""
    state = get_state(ctx)
    if not state.yes and not typer.confirm(f"Revoke token {token_id}?"):
        raise typer.Abort()
    state.project().tokens.revoke(token_id)
    say(state, f"Revoked {token_id}.")
