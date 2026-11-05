"""use, status — the sticky context."""

from __future__ import annotations

import os
from typing import Annotated, Any

import typer
from coho_management_sdk.errors import CohoError
from coho_management_sdk.models import ALL_PERMISSIONS, permissions_for
from rich.markup import escape

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


# How `status` names each credential source (`TokenProvider.source`), for a person reading it.
_SOURCES = {
    "COHO_TOKEN": "COHO_TOKEN",
    "COHO_ACCESS_TOKEN": "COHO_ACCESS_TOKEN",
    "token": "a token given to the client",
    "login": "coho login, refreshed as needed",
    "stored": "coho login --token, not refreshed",
}


def _who(state: State) -> dict[str, Any]:
    """Who the credential is, and what it may do where the context points.

    Every lookup is best effort: signed out, offline, or a context the credential cannot
    see leaves the field None rather than failing `status`, which must always answer.
    """
    c = state.context
    source = state.coho.credential_source
    out: dict[str, Any] = {
        "credential": None,
        "accountRole": None,
        "projectRole": None,
        "permissions": None,
    }
    if source is None:
        return out
    if state.coho.uses_project_token:
        cred: dict[str, Any] = {"kind": "project_token", "source": source}
        try:
            d = state.coho.describe_token()
        except CohoError:
            out["credential"] = cred
            return out
        cred |= {
            "id": d.token_id,
            "label": d.label,
            "expiresAt": d.expires_at,
            "account": d.account_id,
            "accountName": d.account_name,
            "project": d.project_id,
            "projectName": d.project_name,
        }
        out["credential"] = cred
        # A project token holds one role in one project and nothing anywhere else.
        if c.project in (None, d.project_id):
            out["projectRole"] = d.role
            out["permissions"] = list(permissions_for(d.role))
        else:
            out["permissions"] = []
        return out
    cred = {"kind": "person", "source": source}
    try:
        me = state.coho.me()
    except (CohoError, Usage):
        out["credential"] = cred
        return out
    cred |= {"user": me.user_id, "name": me.display_name, "email": me.email}
    out["credential"] = cred
    if not c.account:
        return out
    membership = me.membership(c.account)
    if membership is None:
        return out
    out["accountRole"] = membership.role
    if c.project:
        try:
            summary = next(
                (p for p in state.coho.account(c.account).projects.list() if p.id == c.project),
                None,
            )
        except (CohoError, Usage):
            return out
        role = summary.role if summary else None
        out["projectRole"] = role
        out["permissions"] = list(permissions_for(role))
    return out


def _credential_line(cred: dict[str, Any] | None) -> str:
    if cred is None:
        return "none: run `coho login`, or set COHO_TOKEN"
    source = _SOURCES.get(cred["source"], cred["source"])
    if cred["kind"] == "project_token":
        if "id" not in cred:
            return f"project token, from {source} (not accepted)"
        expires = f", expires {cred['expiresAt'][:10]}" if cred.get("expiresAt") else ""
        label = f' "{escape(cred["label"])}"' if cred.get("label") else ""
        return f"project token{label}, from {source}{expires}"
    if "user" not in cred:
        return f"a person, from {source} (not accepted: run `coho login`)"
    who = cred.get("email") or cred.get("name") or cred["user"]
    return f"{escape(who)}, from {source}"


def _project_role_line(who: dict[str, Any]) -> str | None:
    role = who["projectRole"]
    if role is None:
        return None
    if who["credential"]["kind"] == "project_token":
        return f"{role} (the token's)"
    if role == "owner" and who["accountRole"] == "admin":
        return "owner (as an account admin)"
    return str(role)


def _permissions_line(who: dict[str, Any]) -> str | None:
    perms = who["permissions"]
    if perms is None:
        return None
    if perms == [ALL_PERMISSIONS]:
        return "everything (*)"
    if not perms:
        cred = who["credential"] or {}
        if cred.get("kind") == "project_token":
            return "nothing here: the token works only in its own project"
        return "nothing here"
    return ", ".join(perms)


def status(ctx: typer.Context) -> None:
    """Show the profile, the credential in use, the context, and your role and permissions there.

    The roles and permissions are what the server will allow in the current project, so a
    person or a program can tell what it may do before trying.
    """
    state = get_state(ctx)
    profile = state.profile
    c = state.context
    project_name = profile.project_name(c.account, c.project) if c.account and c.project else None
    account_name = _account_name(state, c.account) if c.account else None
    who = _who(state)
    record(
        state,
        {
            "profile": profile.name,
            "url": state.config.effective_url(profile),
            "credential": who["credential"],
            "account": c.account,
            "accountName": account_name,
            "accountRole": who["accountRole"],
            "project": c.project,
            "projectName": project_name,
            "projectRole": who["projectRole"],
            "ref": c.ref,
            "permissions": who["permissions"],
        },
        [
            ("profile", profile.name),
            ("url", state.config.effective_url(profile) or None),
            ("credential", _credential_line(who["credential"])),
            ("account", f"{account_name} ({c.account})" if account_name else c.account),
            ("account role", who["accountRole"]),
            ("project", f"{project_name}  ({c.project})" if project_name else c.project),
            ("project role", _project_role_line(who)),
            ("ref", c.ref),
            ("permissions", _permissions_line(who)),
        ],
    )
    if state.output != "json" and not c.account:
        console.print("[dim]Set a context with `coho use <account> [<project> [<ref>]]`.[/dim]")
