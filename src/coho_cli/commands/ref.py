"""ref: list, show, switch, describe, deleted, restore — one namespace of branches, tags, envs."""

from __future__ import annotations

from typing import Annotated

import typer

from .._output import record, table
from .._state import Usage, get_state
from .context import save_ref

app = typer.Typer(
    help="Refs: branches, tags and environments share one namespace.", no_args_is_help=True
)


@app.command("list")
def list_(
    ctx: typer.Context,
    kind: Annotated[
        str | None,
        typer.Option("--kind", help="version_branch | feature_branch | tag | environment"),
    ] = None,
) -> None:
    """Every ref in the current project."""
    state = get_state(ctx)
    refs = state.project().refs.list(kind=kind)
    table(
        state,
        {"refs": [r.raw for r in refs]},
        ["REF", "KIND", "TARGET", "DESCRIPTION"],
        [(r.name, r.kind, r.target, r.description) for r in refs],
    )


@app.command("show")
def show(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Argument(help="Default: the current ref.")] = None,
) -> None:
    """One ref. An unset environment is shown with no target."""
    state = get_state(ctx)
    project = state.project()
    r = project.refs.get(name or state.ref().name)
    record(
        state,
        r.raw,
        [("ref", r.name), ("kind", r.kind), ("target", r.target), ("description", r.description)],
    )


@app.command("switch")
def switch(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="A branch, tag or environment.")],
) -> None:
    """Make a ref of the current project the current ref.

    The ref is checked against the server before it is saved, so a typo is an error now
    rather than on the next command. The account and project stay as they are.
    """
    state = get_state(ctx)
    r = state.project().refs.get(name)
    record(state, r.raw, [("ref", r.name), ("kind", r.kind), ("target", r.target)])
    save_ref(state, r.name)


@app.command("describe")
def describe(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument()],
    description: Annotated[
        str | None, typer.Argument(help="Omit, or pass --clear, to clear it.")
    ] = None,
    clear: Annotated[bool, typer.Option("--clear")] = False,
) -> None:
    """Set a ref's standing description (release notes on a tag, purpose on a branch)."""
    state = get_state(ctx)
    r = state.project().refs.describe(name, None if clear else description)
    record(state, r.raw, [("ref", r.name), ("kind", r.kind), ("description", r.description)])


@app.command("deleted")
def deleted(ctx: typer.Context) -> None:
    """Every deleted branch and tag, newest first. An owner's or an organization admin's."""
    state = get_state(ctx)
    refs = state.project().refs.deleted()
    table(
        state,
        {"refs": [r.raw for r in refs]},
        ["REF", "KIND", "STATUS", "DELETED", "NOTE", "ID"],
        [
            (
                r.name,
                r.kind,
                "changed" if r.changed_since_merge else r.status,
                r.deleted_at,
                r.blocked_by or ("name in use: needs --as" if r.name_taken else None),
                r.id,
            )
            for r in refs
        ],
    )


@app.command("restore")
def restore(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="As `coho ref deleted` lists it.")],
    as_name: Annotated[
        str | None,
        typer.Option("--as", help="A branch's new name, if its own has been used since."),
    ] = None,
    deleted_id: Annotated[
        str | None,
        typer.Option("--id", help="Which one, if more than one deleted branch has this name."),
    ] = None,
) -> None:
    """Bring back a deleted branch or tag. An owner's or an organization admin's.

    A branch comes back with its content, its description, and its status. A tag comes back
    under its own name, and can be promoted to once its snapshot has rebuilt.
    """
    state = get_state(ctx)
    refs = state.project().refs
    matches = [r for r in refs.deleted() if r.name == name and deleted_id in (None, r.id)]
    if not matches:
        raise Usage(f"nothing deleted is named '{name}'. See `coho ref deleted`")
    if len(matches) > 1:
        ids = ", ".join(str(r.id) for r in matches)
        raise Usage(f"more than one deleted branch is named '{name}'. Choose with --id: {ids}")
    found = matches[0]
    if found.id is None:
        if as_name:
            raise Usage("a tag comes back under its own name, so --as is for branches")
        r = refs.restore_tag(found.name)
    else:
        r = refs.restore_branch(found.id, name=as_name)
    record(state, r.raw, [("restored", r.name), ("kind", r.kind)])
