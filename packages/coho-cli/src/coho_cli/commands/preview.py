"""preview: entries, entry — the delivery contract, live, through the BFF."""

from __future__ import annotations

from typing import Annotated

import typer

from .._output import emit_json, table
from .._state import get_state

app = typer.Typer(
    help="Preview a ref through the delivery contract, before it is published.",
    no_args_is_help=True,
)


@app.command("entries")
def entries(
    ctx: typer.Context,
    type_: Annotated[str | None, typer.Option("--type", "-t")] = None,
    locale: Annotated[
        str | None, typer.Option("--locale", help="e.g. en-US. Omit for non-localized fields only.")
    ] = None,
    order: Annotated[
        str | None, typer.Option("--order", help="A scalar field; prefix `-` for descending.")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="1..100")] = 25,
    offset: Annotated[int, typer.Option("--offset")] = 0,
) -> None:
    """Entries as delivery would serve them for the current ref."""
    state = get_state(ctx)
    body = (
        state.ref()
        .preview()
        .entries(type=type_, locale=locale, order=order, limit=limit, offset=offset)
    )
    items = body.get("entries") or body.get("items") or []
    table(
        state,
        body,
        ["ID", "TYPE", "SLUG"],
        [
            (e.get("id"), e.get("type") or e.get("_type"), e.get("slug") or e.get("_slug"))
            for e in items
        ],
    )


@app.command("entry")
def entry(
    ctx: typer.Context,
    entry_id: Annotated[str, typer.Argument()],
    locale: Annotated[str | None, typer.Option("--locale")] = None,
) -> None:
    """One entry as delivery would serve it."""
    state = get_state(ctx)
    emit_json(state.ref().preview().entry(entry_id, locale=locale))
