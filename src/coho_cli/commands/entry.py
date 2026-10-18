"""entry: list, get, create, put, delete, history, references."""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer
from coho_management_sdk.models import Entry

from .._entry_ids import entry_id as resolve_entry_id
from .._entry_ids import reference_ids
from .._io import parse_set, read_json, set_path
from .._output import console, emit_json, record, say, table
from .._slugs import content_slug
from .._state import State, Usage, get_state

app = typer.Typer(help="Entries on the current ref.", no_args_is_help=True)

# Every command that takes an entry id takes `@<slug>` too (see `_entry_ids`).
EntryId = Annotated[
    str, typer.Argument(metavar="ID", help="An entry id, or @slug for the entry with that slug.")
]


@app.command("list")
def list_(
    ctx: typer.Context,
    type_: Annotated[
        str | None, typer.Option("--type", "-t", help="Filter by content type slug.")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="1..1000 per page.")] = 100,
    offset: Annotated[int, typer.Option("--offset")] = 0,
    all_: Annotated[bool, typer.Option("--all", help="Follow pages until the end.")] = False,
) -> None:
    """List entries (one page, or --all)."""
    state = get_state(ctx)
    api = state.ref().entries
    if all_:
        entries = list(api.iterate(type=type_, page_size=limit))
        raw: Any = {"entries": [e.raw for e in entries], "total": len(entries)}
    else:
        page = api.list(type=type_, limit=limit, offset=offset)
        entries = page.entries
        raw = page.raw
    table(
        state,
        raw,
        ["ID", "TYPE", "SLUG", "TITLE"],
        [(e.id, e.type, _slug(e), _title(e.fields)) for e in entries],
    )
    if state.output != "json" and not all_ and page.page.has_more:
        console.print(f"[dim]more: --offset {offset + len(entries)}, or --all[/dim]")


@app.command("get")
def get(
    ctx: typer.Context,
    entry_id: EntryId,
    fields_only: Annotated[
        bool,
        typer.Option(
            "--fields", help="Print only the fields object (for editing and `put --file`)."
        ),
    ] = False,
) -> None:
    """One entry, with its ETag."""
    state = get_state(ctx)
    ref = state.ref()
    e = ref.entries.get(resolve_entry_id(ref, entry_id))
    if fields_only:
        emit_json(e.fields)
        return
    if state.output == "json":
        emit_json(e.raw | {"etag": e.etag})
        return
    record(
        state,
        e.raw,
        [
            ("id", e.id),
            ("type", e.type),
            ("slug", _slug(e)),
            ("version", e.version),
            ("etag", e.etag),
        ],
    )
    console.print()
    console.print(json.dumps(e.fields, indent=2, ensure_ascii=False), markup=False, highlight=True)


@app.command("create")
def create(
    ctx: typer.Context,
    type_: Annotated[str, typer.Option("--type", "-t", help="Content type slug.")],
    slug: Annotated[
        str | None,
        typer.Option(
            "--slug",
            "-s",
            help="The entry's slug, stamped as `_slug`. Omit it to build one from `_name`.",
        ),
    ] = None,
    file: Annotated[
        str | None,
        typer.Option("--file", "-f", help="Fields JSON: path, `-` for stdin, or inline."),
    ] = None,
    set_: Annotated[
        list[str] | None,
        typer.Option(
            "--set", help="path=value; JSON values parse, e.g. --set title.en-US=Hello --set rank=3"
        ),
    ] = None,
) -> None:
    """Create an entry from a fields document and/or --set values.

    With no --slug, the slug is built from `_name` in kebab-case ("Hello, World!" ->
    hello-world). The slug is fixed once created; renaming `_name` does not change it.
    """
    state = get_state(ctx)
    ref = state.ref()
    fields = _fields(file, reference_ids(ref, lambda: type_, _parse_sets(set_)))
    if slug is None:
        name = fields.get("_name")
        if not isinstance(name, str) or not name.strip():
            raise Usage("no --slug given and the entry has no _name to build one from")
        slug = content_slug(name)
    e = ref.entries.create(type=type_, slug=slug, fields=fields)
    _created_or_updated(state, e)


@app.command("put")
def put(
    ctx: typer.Context,
    entry_id: EntryId,
    file: Annotated[
        str | None, typer.Option("--file", "-f", help="Fields JSON (replaces all fields).")
    ] = None,
    set_: Annotated[
        list[str] | None,
        typer.Option("--set", help="path=value, applied on top of the current fields."),
    ] = None,
    if_match: Annotated[
        str | None, typer.Option("--if-match", help="ETag from your last `entry get`.")
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite whatever version is current.")
    ] = False,
) -> None:
    """Update an entry's fields.

    With --file, the document replaces the fields wholesale and needs --if-match (or
    --force). With only --set, the current entry is read first, patched, and written
    back with its own ETag — a read-modify-write that fails with VERSION_CONFLICT if
    somebody else wrote in between.
    """
    state = get_state(ctx)
    if file is None and not set_:
        raise Usage("nothing to write: pass --file and/or --set")
    ref = state.ref()
    api = ref.entries
    entry_id = resolve_entry_id(ref, entry_id)
    if file is not None:
        sets = reference_ids(ref, lambda: api.get(entry_id).type, _parse_sets(set_))
        fields = _fields(file, sets)
        e = api.put(entry_id, fields, if_match=if_match, force=force)
    else:
        current = api.get(entry_id)
        for path, value in reference_ids(ref, lambda: current.type, _parse_sets(set_)):
            set_path(current.fields, path, value)
        e = api.put(current, if_match=if_match)
    _created_or_updated(state, e)


@app.command("delete")
def delete(
    ctx: typer.Context,
    entry_id: EntryId,
    if_match: Annotated[str | None, typer.Option("--if-match")] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Delete whatever version is current.")
    ] = False,
) -> None:
    """Tombstone an entry. Never a physical delete; the tombstone has its own ETag."""
    state = get_state(ctx)
    ref = state.ref()
    api = ref.entries
    named = entry_id
    entry_id = resolve_entry_id(ref, entry_id)
    what = entry_id if named == entry_id else f"{named} ({entry_id})"
    if not state.yes and not typer.confirm(f"Delete entry {what} on {state.context.ref}?"):
        raise typer.Abort()
    refs = api.references(entry_id)
    if (
        refs.total
        and not state.yes
        and not typer.confirm(f"{refs.total} entries still link to it. Continue?")
    ):
        raise typer.Abort()
    etag = api.delete(entry_id, if_match=if_match, force=force or (if_match is None))
    if state.output == "json":
        emit_json({"id": entry_id, "etag": etag})
    else:
        say(state, f"Deleted {entry_id} (tombstone {etag}).")


@app.command("history")
def history(
    ctx: typer.Context,
    entry_id: EntryId,
    limit: Annotated[int, typer.Option("--limit")] = 50,
    offset: Annotated[int, typer.Option("--offset")] = 0,
) -> None:
    """Version history on this ref, newest first. Tombstones included."""
    state = get_state(ctx)
    ref = state.ref()
    h = ref.entries.history(resolve_entry_id(ref, entry_id), limit=limit, offset=offset)
    table(
        state,
        h.raw,
        ["SEQ", "OP", "VERSION", "BRANCH", "ACTOR", "AT"],
        [(v.seq, v.op, v.version, v.branch, v.actor, v.at) for v in h.versions],
    )


@app.command("references")
def references(ctx: typer.Context, entry_id: EntryId) -> None:
    """What links to this entry on this ref. Complete, never paginated."""
    state = get_state(ctx)
    ref = state.ref()
    r = ref.entries.references(resolve_entry_id(ref, entry_id))
    table(
        state,
        r.raw,
        ["FROM", "KIND", "SLUG", "FIELD"],
        [(i.node_id, i.kind, i.slug, i.field) for i in r.incoming],
        empty="(nothing links here)",
    )


# -- helpers ---------------------------------------------------------------------


def _parse_sets(sets: list[str] | None) -> list[tuple[str, Any]]:
    return [parse_set(spec) for spec in sets or []]


def _fields(file: str | None, sets: list[tuple[str, Any]]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if file is not None:
        doc = read_json(file, what="fields")
        if not isinstance(doc, dict):
            raise Usage("fields must be a JSON object")
        if "fields" in doc and set(doc) <= {"fields", "type", "slug", "id", "version", "etag"}:
            inner = doc.get("fields")
            fields = dict(inner) if isinstance(inner, dict) else {}
        else:
            fields = dict(doc)
    for path, value in sets:
        set_path(fields, path, value)
    if not fields:
        raise Usage("no fields given: pass --file and/or --set")
    return fields


def _created_or_updated(state: State, e: Entry) -> None:
    if state.output == "json":
        emit_json(e.raw | {"etag": e.etag})
    else:
        record(
            state,
            e.raw,
            [
                ("id", e.id),
                ("type", e.type),
                ("slug", _slug(e)),
                ("version", e.version),
                ("etag", e.etag),
            ],
        )


def _slug(e: Entry) -> str | None:
    # ⚠️ authoring.yaml says an entry carries `slug`, but authoring's EntryResponse does not
    # send it yet. `_slug` in the fields is the same value, stamped by the writer.
    slug = e.slug or e.fields.get("_slug")
    return slug if isinstance(slug, str) else None


def _title(fields: dict[str, Any]) -> str | None:
    for key in ("title", "name", "headline", "_name"):
        v = fields.get(key)
        if isinstance(v, dict):
            v = next(iter(v.values()), None)
        if isinstance(v, str):
            return v[:60]
    return None
