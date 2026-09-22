"""type: list, get, put, delete — content types on a ref."""

from __future__ import annotations

from typing import Annotated

import typer

from .._io import read_json
from .._output import console, emit_json, record, say, table
from .._state import Usage, get_state

app = typer.Typer(help="Content types, as resolved on the current ref.", no_args_is_help=True)


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """Content types on the current ref."""
    state = get_state(ctx)
    types = state.ref().types.list()
    table(
        state,
        {"types": [t.raw for t in types]},
        ["TYPE", "NAME", "FIELDS", "VERSION"],
        [(t.slug, t.name, ", ".join(f.get("id", "?") for f in t.fields), t.version) for t in types],
    )


@app.command("get")
def get(ctx: typer.Context, slug: Annotated[str, typer.Argument()]) -> None:
    """One content type, with its ETag."""
    state = get_state(ctx)
    t = state.ref().types.get(slug)
    if state.output == "json":
        emit_json(t.raw | {"etag": t.etag})
        return
    record(
        state, t.raw, [("type", t.slug), ("name", t.name), ("version", t.version), ("etag", t.etag)]
    )
    console.print()
    table(
        state,
        t.raw,
        ["FIELD", "TYPE", "REQUIRED", "LOCALIZED", "OF", "MANY"],
        [
            (
                f.get("id"),
                f.get("type"),
                f.get("required", False),
                f.get("localized", False),
                f.get("of"),
                f.get("many", False),
            )
            for f in t.fields
        ],
    )


@app.command("put")
def put(
    ctx: typer.Context,
    slug: Annotated[str, typer.Argument()],
    file: Annotated[
        str,
        typer.Option("--file", "-f", help="The definition: a path, `-` for stdin, or inline JSON."),
    ],
    if_match: Annotated[
        str | None, typer.Option("--if-match", help="ETag from your last `type get`.")
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite whatever version is current.")
    ] = False,
    confirm_destructive: Annotated[
        bool, typer.Option("--confirm-destructive", help="Allow field/locale removal.")
    ] = False,
) -> None:
    """Create or update a content type from a JSON definition.

    The file holds the definition itself (`{"_name": …, "fields": […]}`) or a wrapper
    `{"definition": …}`. Creating needs no ETag; updating needs --if-match or --force.
    """
    state = get_state(ctx)
    doc = read_json(file, what="definition")
    if not isinstance(doc, dict):
        raise Usage("the definition must be a JSON object")
    definition = doc["definition"] if "definition" in doc and "fields" not in doc else doc
    confirm = confirm_destructive or bool(doc.get("confirmDestructive"))
    api = state.ref().types
    etag = if_match
    if etag is None and not force:
        # Creating vs updating: if the type exists, an update without a precondition would be 428.
        existing = api._current_etag(slug)
        if existing:
            raise Usage(
                f"type '{slug}' exists; pass --if-match {existing} "
                f"(from `coho type get {slug}`) or --force"
            )
    t = api.put(slug, definition, if_match=etag, confirm_destructive=confirm, force=force)
    if state.output == "json":
        emit_json(t.raw | {"etag": t.etag})
    else:
        record(
            state,
            t.raw,
            [("type", t.slug), ("name", t.name), ("version", t.version), ("etag", t.etag)],
        )


@app.command("delete")
def delete(
    ctx: typer.Context,
    slug: Annotated[str, typer.Argument()],
    confirm_destructive: Annotated[
        bool, typer.Option("--confirm-destructive", help="Orphan its entries deliberately.")
    ] = False,
) -> None:
    """Tombstone a content type. Refused while entries still resolve to it."""
    state = get_state(ctx)
    if not state.yes and not typer.confirm(f"Delete type {slug} on {state.context.ref}?"):
        raise typer.Abort()
    state.ref().types.delete(slug, confirm_destructive=confirm_destructive)
    say(state, f"Deleted type {slug}.")
