"""use, status — the sticky context."""

from __future__ import annotations

import os
from typing import Annotated

import typer
from coho_management_sdk.errors import CohoError

from .._output import console, record, say, warn
from .._state import State, Usage, get_state


def _account_name(state: State, account_id: str) -> str | None:
    """The account's name, from the server. None when it can't be had (signed out, offline),
    so `status` falls back to the id alone rather than failing."""
    try:
        return next(
            (m.account_name for m in state.coho.accounts() if m.account_id == account_id), None
        )
    except (CohoError, Usage):
        return None


def save_ref(state: State, name: str) -> None:
    """Make ``name`` the saved ref, as `ref switch` and `branch create` do.

    The saved ref comes last: a --ref or COHO_REF still wins, so `coho status` would not
    show the switch. Say so, rather than look as if the switch did nothing.
    """
    state.profile.context.ref = name
    state.save()
    say(state, f"Context ref is now [bold]{name}[/bold].")
    override = state.overrides.ref
    if override and override != name:
        given = (
            f"COHO_REF={override}"
            if os.environ.get("COHO_REF") == override
            else f"--ref {override}"
        )
        warn(f"{given} overrides the saved ref, so commands still use {override}")


def use(
    ctx: typer.Context,
    account: Annotated[str | None, typer.Argument(help="Account id or name.")] = None,
    project: Annotated[str | None, typer.Argument(help="Project name or id.")] = None,
    ref: Annotated[str | None, typer.Argument(help="Branch, tag or environment.")] = None,
    clear: Annotated[bool, typer.Option("--clear", help="Forget the saved context.")] = False,
) -> None:
    """Set the account, project and ref every command uses by default.

    Each argument is checked against the server before it is saved, so a typo is a
    usage error now rather than a 404 later. Giving fewer arguments keeps the rest:
    `coho use acme` keeps the project and ref if they still belong to that account.
    """
    state = get_state(ctx)
    profile = state.profile
    if clear:
        profile.context.account = profile.context.project = profile.context.ref = None
        state.save()
        say(state, "Context cleared.")
        return
    if account is None:
        raise Usage("usage: coho use <account> [<project> [<ref>]]  (or --clear)")

    acct = state.coho.account(account)
    if profile.context.account != acct.id:
        profile.context.project = None
        profile.context.ref = None
    profile.context.account = acct.id

    if project is not None:
        pid = state.resolve_project_id(acct, project)
        proj = acct.project(pid)
        info = proj.info()  # verifies it exists and that we can see it
        profile.remember_project(acct.id, info.name, info.id)
        if profile.context.project != info.id:
            profile.context.ref = None
        profile.context.project = info.id
    if ref is not None:
        if not profile.context.project:
            raise Usage("a ref needs a project: coho use <account> <project> <ref>")
        proj = acct.project(profile.context.project)
        proj.refs.get(ref)  # verifies
        profile.context.ref = ref
    state.save()
    status(ctx)


def status(ctx: typer.Context) -> None:
    """Show the current profile and context."""
    state = get_state(ctx)
    profile = state.profile
    c = state.context
    project_name = profile.project_name(c.account, c.project) if c.account and c.project else None
    account_name = _account_name(state, c.account) if c.account else None
    record(
        state,
        {
            "profile": profile.name,
            "url": state.config.effective_url(profile),
            "account": c.account,
            "accountName": account_name,
            "project": c.project,
            "projectName": project_name,
            "ref": c.ref,
        },
        [
            ("profile", profile.name),
            ("url", state.config.effective_url(profile) or None),
            ("account", f"{account_name} ({c.account})" if account_name else c.account),
            ("project", f"{project_name}  ({c.project})" if project_name else c.project),
            ("ref", c.ref),
        ],
    )
    if state.output != "json" and not c.account:
        console.print("[dim]Set a context with `coho use <account> [<project> [<ref>]]`.[/dim]")
