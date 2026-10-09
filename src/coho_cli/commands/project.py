"""project: create, show, list, register, forget."""

from __future__ import annotations

from typing import Annotated, Any

import typer
from coho_management_sdk.models import ProjectInfo

from .._output import console, record, say, table
from .._state import State, Usage, get_state

app = typer.Typer(help="Projects in the current account.", no_args_is_help=True)


@app.command("create")
def create(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument()],
    use: Annotated[
        bool, typer.Option("--use/--no-use", help="Make it the current project.")
    ] = True,
) -> None:
    """Create and bootstrap a project: trunk `v0.0.x`, environments dev/qa/stage/prod."""
    state = get_state(ctx)
    acct = state.account()
    project = acct.projects.create(name)
    info = project.info()
    state.profile.remember_project(acct.id, info.name, info.id)
    if use:
        state.profile.context.project = info.id
        state.profile.context.ref = info.trunk
    state.save()
    _show(state, info.raw, info)
    if use:
        say(
            state,
            f"\nContext is now project [bold]{info.name}[/bold] on ref [bold]{info.trunk}[/bold].",
        )


@app.command("show")
def show(
    ctx: typer.Context,
    project: Annotated[
        str | None, typer.Argument(help="Id or known name; default: current.")
    ] = None,
) -> None:
    """One project: trunk and environments."""
    state = get_state(ctx)
    acct = state.account()
    pid = state.profile.resolve_project(acct.id, project) if project else None
    proj = acct.project(pid) if pid else state.project()
    info = proj.info()
    state.profile.remember_project(acct.id, info.name, info.id)
    state.save()
    _show(state, info.raw, info)


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """Projects you can open in the current account, and your role on each.

    The server's list, plus any project this CLI remembers locally (from
    `coho project register`) that the server does not list for you, marked
    `local only`: it was deleted, or your access was taken away.
    """
    state = get_state(ctx)
    acct = state.account()
    server = acct.projects.list()
    on_server = {p.id for p in server}
    local_only = {
        name: pid
        for name, pid in state.profile.projects.get(acct.id, {}).items()
        if pid not in on_server
    }
    current = state.context.project
    entries: list[dict[str, str | None]] = [
        {"name": p.name, "id": p.id, "role": p.role, "source": "server"} for p in server
    ]
    entries += [
        {"name": n, "id": i, "role": None, "source": "local"} for n, i in sorted(local_only.items())
    ]
    table(
        state,
        {"account": acct.id, "projects": entries},
        ["", "PROJECT", "ID", "ROLE"],
        [
            ("*" if e["id"] == current else "", e["name"], e["id"], e["role"] or "local only")
            for e in entries
        ],
        empty="(no projects yet — create one with `coho project create <name>`)",
    )


@app.command("register")
def register(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument()],
    name: Annotated[str | None, typer.Argument()] = None,
) -> None:
    """Remember a project id under a name, after checking it exists."""
    state = get_state(ctx)
    acct = state.account()
    info = acct.project(project_id).info()
    state.profile.remember_project(acct.id, name or info.name, info.id)
    state.save()
    say(state, f"Registered [bold]{name or info.name}[/bold] → {info.id}.")


@app.command("forget")
def forget(ctx: typer.Context, project: Annotated[str, typer.Argument(help="Name or id.")]) -> None:
    """Drop a project from the local registry. Nothing happens on the server."""
    state = get_state(ctx)
    acct = state.account()
    if not state.profile.forget_project(acct.id, project):
        raise Usage(f"'{project}' is not in the local registry")
    state.save()
    say(state, f"Forgot {project}.")


def _show(state: State, raw: dict[str, Any], info: ProjectInfo) -> None:
    record(state, raw, [("id", info.id), ("name", info.name), ("trunk", info.trunk)])
    if state.output != "json":
        console.print()
        table(
            state,
            raw,
            ["ENVIRONMENT", "TARGET"],
            [(e.get("name"), e.get("target") or "(unset)") for e in info.environments],
        )
