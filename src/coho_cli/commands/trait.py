"""trait: list, get, put, delete — traits on a ref: named groups of fields that types take."""

from __future__ import annotations

from typing import Annotated

import typer

from .._io import read_json
from .._output import console, emit_json, record, say, table
from .._slugs import type_slug
from .._state import Usage, get_state

app = typer.Typer(
    help="Traits, as resolved on the current ref: groups of fields types take by `traits`.",
    no_args_is_help=True,
)


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """Traits on the current ref, and the types that take each."""
    state = get_state(ctx)
    ref = state.ref()
    traits = ref.traits.list()
    types = ref.types.list()
    table(
        state,
        {"traits": [t.raw for t in traits]},
        ["TRAIT", "NAME", "FIELDS", "TAKEN BY", "VERSION"],
        [
            (
                t.slug,
                t.name,
                ", ".join(f.get("id", "?") for f in t.fields),
                ", ".join(sorted(ty.slug for ty in types if t.slug in ty.traits)),
                t.version,
            )
            for t in traits
        ],
    )


@app.command("get")
def get(ctx: typer.Context, slug: Annotated[str, typer.Argument()]) -> None:
    """One trait, with its ETag and its fields."""
    state = get_state(ctx)
    t = state.ref().traits.get(slug)
    if state.output == "json":
        emit_json(t.raw | {"etag": t.etag})
        return
    record(
        state,
        t.raw,
        [("trait", t.slug), ("name", t.name), ("version", t.version), ("etag", t.etag)],
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
    file: Annotated[
        str,
        typer.Option("--file", "-f", help="The definition: a path, `-` for stdin, or inline JSON."),
    ],
    if_match: Annotated[
        str | None, typer.Option("--if-match", help="ETag from your last `trait get`.")
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite whatever version is current.")
    ] = False,
    confirm_destructive: Annotated[
        bool,
        typer.Option(
            "--confirm-destructive", help="Allow a change that costs a type that takes it content."
        ),
    ] = False,
    slug: Annotated[
        str | None,
        typer.Argument(
            help="The trait's slug. Omit it to build one from the definition's _name, camelCase."
        ),
    ] = None,
) -> None:
    """Create or update a trait from a JSON definition.

    The file holds `{"_name": …, "fields": […]}`, or a wrapper `{"definition": …}`, and
    nothing else: a trait has no `extends`, `abstract`, `overrides` or `traits`. A type
    takes it by naming it in its own `traits`.

    A trait's change reaches every type that takes it and every type below them. One that
    would lose or invalidate their content is refused, naming those types and how many
    entries, unless --confirm-destructive.
    """
    state = get_state(ctx)
    doc = read_json(file, what="definition")
    if not isinstance(doc, dict):
        raise Usage("the definition must be a JSON object")
    definition = doc["definition"] if "definition" in doc and "fields" not in doc else doc
    confirm = confirm_destructive or bool(doc.get("confirmDestructive"))
    if slug is None:
        name = definition.get("_name") if isinstance(definition, dict) else None
        if not isinstance(name, str) or not name.strip():
            raise Usage("no SLUG given and the definition has no _name to build one from")
        slug = type_slug(name)
    api = state.ref().traits
    if if_match is None and not force:
        # Creating vs updating: if the trait exists, an update without a precondition would be 428.
        existing = api._current_etag(slug)
        if existing:
            raise Usage(
                f"trait '{slug}' exists; pass --if-match {existing} "
                f"(from `coho trait get {slug}`) or --force"
            )
    t = api.put(slug, definition, if_match=if_match, confirm_destructive=confirm, force=force)
    if state.output == "json":
        emit_json(t.raw | {"etag": t.etag})
    else:
        record(
            state,
            t.raw,
            [("trait", t.slug), ("name", t.name), ("version", t.version), ("etag", t.etag)],
        )


@app.command("delete")
def delete(ctx: typer.Context, slug: Annotated[str, typer.Argument()]) -> None:
    """Tombstone a trait. Refused while any type takes it: remove it from those first."""
    state = get_state(ctx)
    if not state.yes and not typer.confirm(f"Delete trait {slug} on {state.context.ref}?"):
        raise typer.Abort()
    state.ref().traits.delete(slug)
    say(state, f"Deleted trait {slug}.")
