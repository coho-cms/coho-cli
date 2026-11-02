"""pin: list, add, remove, order — your pinned entries in the current project."""

from __future__ import annotations

from typing import Annotated

import typer

from .._entry_ids import entry_id as resolve_entry_id
from .._output import emit_json, say, table
from .._state import State, get_state

app = typer.Typer(
    help="Your pinned entries in the current project: the ones the console keeps at hand.",
    no_args_is_help=True,
)

# As `entry` takes them: an id, `@<slug>`, or a singleton type's slug, looked up on the
# current ref.
EntryId = Annotated[
    str,
    typer.Argument(
        metavar="ID",
        help="An entry id, @slug for the entry with that slug, or a singleton type's slug.",
    ),
]


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """Your pins, top first, each as it reads on the current ref."""
    state = get_state(ctx)
    ref = state.ref()
    pins = state.project().pins.list(ref.name)
    table(
        state,
        pins.raw,
        ["ID", "STATE", "TYPE", "SLUG", "NAME"],
        [(p.entry_id, _state(p.state), p.type, p.slug, p.name) for p in pins.pins],
        empty="(no pins)",
    )


@app.command("add")
def add(ctx: typer.Context, entry_id: EntryId) -> None:
    """Pin an entry, on top. Pinning one already pinned changes nothing."""
    state = get_state(ctx)
    ref = state.ref()
    resolved = resolve_entry_id(ref, entry_id)
    state.project().pins.add(resolved)
    _done(state, "pinned", entry_id, resolved)


@app.command("remove")
def remove(ctx: typer.Context, entry_id: EntryId) -> None:
    """Unpin an entry. One not pinned is not an error.

    A slug resolves on the current ref, so an entry deleted here is unpinned by its id,
    which `coho pin list` shows.
    """
    state = get_state(ctx)
    ref = state.ref()
    resolved = resolve_entry_id(ref, entry_id)
    state.project().pins.remove(resolved)
    _done(state, "unpinned", entry_id, resolved)


@app.command("order")
def order(
    ctx: typer.Context,
    entry_ids: Annotated[
        list[str],
        typer.Argument(
            metavar="ID...", help="Every pinned entry, top first: ids, @slugs, or singletons."
        ),
    ],
) -> None:
    """Set the whole order, top first, naming every pinned entry once and nothing else."""
    state = get_state(ctx)
    ref = state.ref()
    resolved = [resolve_entry_id(ref, e) for e in entry_ids]
    state.project().pins.order(resolved)
    if state.output == "json":
        emit_json({"entries": resolved})
    else:
        say(state, f"Pins ordered: {len(resolved)}.")


def _state(state: str) -> str:
    # Pins are the project's, so one can name an entry this ref does not have.
    return {"deleted": "deleted here", "absent": "not on this ref"}.get(state, state)


def _done(state: State, verb: str, named: str, resolved: str) -> None:
    if state.output == "json":
        emit_json({"entryId": resolved, verb: True})
        return
    what = resolved if named == resolved else f"{named} ({resolved})"
    say(state, f"{verb.capitalize()} {what}.")
