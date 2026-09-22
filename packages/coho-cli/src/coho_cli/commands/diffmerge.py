"""diff, merge."""

from __future__ import annotations

from typing import Annotated

import typer

from coho_sdk.errors import MergeConflict
from coho_sdk.models import Resolution

from .._io import read_json
from .._output import console, emit_json, err, record, table
from .._state import Usage, get_state


def diff(
    ctx: typer.Context,
    from_ref: Annotated[
        str, typer.Argument(metavar="FROM", help="The target side of a prospective merge.")
    ],
    to_ref: Annotated[
        str | None,
        typer.Argument(metavar="TO", help="The branch under review. Default: the current ref."),
    ] = None,
    absolute: Annotated[
        bool, typer.Option("--absolute", help="Two-dot: compare tips instead of since divergence.")
    ] = False,
    fields: Annotated[bool, typer.Option("--fields", help="Show field-level changes.")] = False,
) -> None:
    """Compare two refs. Three-dot by default, with the merge preview and its conflicts."""
    state = get_state(ctx)
    to = to_ref or state.context.ref
    if not to:
        raise Usage("TO is required when no ref is in context")
    d = state.project().diff(from_ref, to, mode="absolute" if absolute else "diverged")
    if state.output == "json":
        emit_json(d.raw)
        return
    base = f"{d.base.get('ref')}@{d.base.get('seq')}" if d.base else None
    record(
        state,
        d.raw,
        [
            ("from", d.from_ref),
            ("to", d.to_ref),
            ("mode", d.mode),
            ("base", base),
            ("added", d.added),
            ("modified", d.modified),
            ("deleted", d.deleted),
            ("conflicts", len(d.conflicts)),
            ("merge token", d.merge_token),
        ],
    )
    console.print()
    table(
        state,
        d.raw,
        ["CHANGE", "KIND", "SLUG", "NODE"],
        [(n.change, n.kind, n.slug, n.node_id) for n in d.nodes],
        empty="(no changes)",
    )
    if fields:
        for n in d.nodes:
            for f in n.fields:
                console.print(
                    f"  {n.slug or n.node_id}  {f.get('change'):8} {f.get('path')}", highlight=False
                )
                if "before" in f or "after" in f:
                    console.print(
                        f"      - {f.get('before')!r}\n      + {f.get('after')!r}",
                        highlight=False,
                        markup=False,
                    )
    if d.conflicts:
        console.print()
        console.print("[yellow]conflicts[/yellow] (merge will refuse until resolved):")
        table(
            state,
            d.raw,
            ["SLUG", "REASON", "PATHS", "NODE"],
            [(c.slug, c.reason, c.paths, c.node_id) for c in d.conflicts],
        )


def merge(
    ctx: typer.Context,
    source: Annotated[
        str | None, typer.Argument(help="The branch to merge. Default: the current ref.")
    ] = None,
    into: Annotated[
        str | None, typer.Option("--into", help="The target branch (e.g. the trunk).")
    ] = None,
    message: Annotated[
        str | None, typer.Option("--message", "-m", help="What this merge does. Write-once.")
    ] = None,
    resolve: Annotated[
        str | None,
        typer.Option(
            "--resolve",
            help="Resolutions JSON: a path, `-`, or inline. See docs/commands/merge.md.",
        ),
    ] = None,
    expected_token: Annotated[
        str | None,
        typer.Option("--expected-token", help="The mergeToken from the diff you reviewed."),
    ] = None,
    reviewed: Annotated[
        bool,
        typer.Option("--reviewed", help="Run the diff first and pass its token automatically."),
    ] = False,
) -> None:
    """Three-way merge one branch into another. Lands whole or is refused whole.

    On MERGE_CONFLICT the conflicts are printed (JSON with --output json). Write a
    resolutions file naming, per node and path, `source`, `target` or a `value`, and
    pass it with --resolve.
    """
    state = get_state(ctx)
    src = source or state.context.ref
    if not src:
        raise Usage("SOURCE is required when no ref is in context")
    if not into:
        raise Usage("--into is required")
    project = state.project()
    resolutions: list[Resolution] | None = None
    if resolve:
        doc = read_json(resolve, what="resolutions")
        items = doc.get("resolutions") if isinstance(doc, dict) else doc
        if not isinstance(items, list):
            raise Usage('resolutions must be a JSON array (or {"resolutions": [...]})')
        resolutions = [Resolution.from_dict(r) for r in items]
    token = expected_token
    if reviewed and not token:
        token = project.diff(into, src).merge_token
    try:
        result = project.merge(
            src, into, message=message, resolutions=resolutions, expected_token=token
        )
    except MergeConflict as exc:
        if state.output == "json":
            emit_json(exc.problem)
            raise typer.Exit(code=4) from None
        raise
    if state.output == "json":
        emit_json(result.raw)
        return
    record(
        state,
        result.raw,
        [
            ("source", result.source),
            ("target", result.target),
            ("merged", result.merged),
            ("unchanged", result.unchanged),
            ("resolved", result.resolved),
        ],
    )
    err.print(f"[green]Merged {result.source} into {result.target}.[/green]")
