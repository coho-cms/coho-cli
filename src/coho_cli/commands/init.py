"""init — files a repository keeps about its Coho project."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from coho_management_sdk.errors import CohoError

from .. import _agents
from .._output import emit_json, say, warn
from .._state import State, Usage, get_state


def init(
    ctx: typer.Context,
    agents: Annotated[
        bool,
        typer.Option(
            "--agents",
            help="Write COHO.md, describing the live project for coding agents, and point "
            "AGENTS.md and CLAUDE.md at it.",
        ),
    ] = False,
    directory: Annotated[
        Path,
        typer.Option(
            "--dir", help="The repository to write into.", file_okay=False, resolve_path=True
        ),
    ] = Path("."),
    ref: Annotated[
        str | None,
        typer.Option("--ref", help="Read the content types from this ref (default: the trunk)."),
    ] = None,
    check: Annotated[
        bool,
        typer.Option(
            "--check", help="Write nothing; exit 1 if the files are not what this would write."
        ),
    ] = False,
) -> None:
    """Write files that describe this Coho project to tools in a repository.

    `--agents` reads the project (its content types and fields, the locales its entries
    use, its refs and environments) and writes COHO.md, with the rules for changing
    content safely. AGENTS.md and CLAUDE.md get a marked block pointing at it, merged
    without touching the rest of either file. Run it again whenever the content model
    changes, and commit the result: the file never drifts from the project, the way a
    hand-written one does.

    Which project: --account and --project (or COHO_ACCOUNT, COHO_PROJECT) when given;
    else the one an existing COHO.md names, so regenerating is the same project on any
    machine; else coho.config.json's, for @coho-cms/codegen; else the saved context.
    """
    if not agents:
        raise Usage(
            "say what to write: `coho init --agents` writes COHO.md for coding agents. "
            "See `coho init --help`."
        )
    state = get_state(ctx)
    if not directory.is_dir():
        raise Usage(f"{directory} is not a directory")
    source = _source(state, directory, ref or state.overrides.ref)
    account_name = _account_name(state, source.account)
    snapshot = _agents.gather(state.coho, source, account_name=account_name)
    regenerate = "coho init --agents" + (f" --ref {source.ref}" if source.ref else "")
    files = {_agents.COHO_MD: _agents.render(snapshot, regenerate=regenerate)}
    if _agents.read(directory / _agents.COHO_MD) == files[_agents.COHO_MD]:
        del files[_agents.COHO_MD]
    files |= _agents.plan_pointers(directory)

    outcome = {
        name: (
            "unchanged"
            if name not in files
            else "updated"
            if (directory / name).exists()
            else "created"
        )
        for name in (_agents.COHO_MD, _agents.AGENTS_MD, _agents.CLAUDE_MD)
        if name in files or (directory / name).exists()
    }
    if check:
        stale = sorted(files)
        if state.output == "json":
            emit_json({"upToDate": not stale, "stale": stale})
        elif stale:
            warn(f"out of date: {', '.join(stale)}. Run `{regenerate}` and commit the result.")
        else:
            say(state, "COHO.md and its pointers are up to date.")
        if stale:
            raise typer.Exit(1)
        return

    for name, text in files.items():
        (directory / name).write_text(text, encoding="utf-8", newline="")
    content = sum(1 for t in snapshot.types if t.raw.get("kind") != "component")
    components = len(snapshot.types) - content
    if state.output == "json":
        emit_json(
            {
                "files": outcome,
                "account": source.account,
                "project": source.project,
                "ref": snapshot.ref,
                "contentTypes": content,
                "componentTypes": components,
                "locales": [loc for loc, _ in snapshot.locales],
            }
        )
        return
    for name, what in outcome.items():
        say(state, f"{what.capitalize()} {name}")
    locales = ", ".join(loc for loc, _ in snapshot.locales) or "none yet"
    say(
        state,
        f"{snapshot.project_name} on {snapshot.ref}: {content} content types, {components} "
        f"component types; locales {locales}. Commit the files, and run this again after the "
        "content model changes.",
    )


def _source(state: State, directory: Path, ref: str | None) -> _agents.Source:
    url = state.url or state.config.effective_url(state.profile)
    overridden = state.overrides.account or state.overrides.project
    recorded = (
        None
        if overridden
        else (_agents.recorded_source(directory) or _agents.codegen_source(directory))
    )
    if recorded is not None:
        if recorded.url and url and recorded.url.rstrip("/") != url.rstrip("/"):
            warn(
                f"{_agents.COHO_MD} describes a project on {recorded.url}, but this profile "
                f"reaches {url}. Pass -p or --url to use the other server."
            )
        return _agents.Source(url, recorded.account, recorded.project, ref or recorded.ref)
    project = state.project()  # the context: overrides, then what `coho use` saved
    return _agents.Source(url, project.account.id, project.id, ref)


def _account_name(state: State, account_id: str) -> str | None:
    if state.coho.uses_project_token:
        return None  # the token describes itself, in gather()
    try:
        membership = state.coho.me().membership(account_id)
    except CohoError:
        return None
    return membership.account_name if membership else None
