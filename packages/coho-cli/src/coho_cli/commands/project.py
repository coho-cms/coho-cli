"""project: create, show, list (local registry), register, forget."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from coho_sdk.models import ProjectInfo

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
    """Projects this CLI knows in the current account.

    ⚠️ The server has no project listing yet, so this is a local registry: projects
    you created or opened with `coho use`/`coho project show`, plus any you
    `coho project register`. It is per profile and per account.
    """
    state = get_state(ctx)
    acct = state.account()
    known = state.profile.projects.get(acct.id, {})
    current = state.context.project
    table(
        state,
        {"account": acct.id, "projects": [{"name": n, "id": i} for n, i in known.items()]},
        ["", "PROJECT", "ID"],
        [("*" if i == current else "", n, i) for n, i in sorted(known.items())],
        empty="(none known locally — create one, or `coho project register <name> <id>`)",
    )
    if state.output != "json" and known:
        console.print("[dim]Local registry; the server does not list projects yet.[/dim]")


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
