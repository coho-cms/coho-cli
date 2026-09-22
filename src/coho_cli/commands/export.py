"""export."""

from __future__ import annotations

from typing import Annotated

import typer

from .._output import record
from .._state import Usage, get_state


def export(
    ctx: typer.Context,
    ref: Annotated[
        str | None, typer.Argument(help="A tag or a branch. Default: the current ref.")
    ] = None,
    format_: Annotated[
        str, typer.Option("--format", help="`ndjson` (default) or `tar`.")
    ] = "ndjson",
    output: Annotated[
        str | None,
        typer.Option("--out", "-o", help="Output file. Default: <ref>.<format>. `-` for stdout."),
    ] = None,
    stream: Annotated[
        bool, typer.Option("--stream", help="Force bytes through the API instead of a redirect.")
    ] = False,
) -> None:
    """Export a tag (its prebuilt image) or a branch (computed at its tip).

    A branch's tip moves, so the sequence the export was resolved at is reported.
    Nothing exported is importable yet; the manifest says so.
    """
    import sys

    state = get_state(ctx)
    name = ref or state.context.ref
    if not name:
        raise Usage("REF is required when no ref is in context")
    if format_ not in ("ndjson", "tar"):
        raise Usage("--format must be `ndjson` or `tar`")
    project = state.project()
    sink = sys.stdout.buffer if output == "-" else output
    result = project.export(name, format=format_, to=sink, stream=stream or None)
    if output == "-":
        return
    record(
        state,
        {
            "ref": result.ref,
            "format": result.format,
            "path": result.path,
            "seq": result.seq,
            "bytes": result.bytes_written,
            "manifest": result.manifest,
        },
        [
            ("ref", result.ref),
            ("format", result.format),
            ("written", result.path),
            ("bytes", result.bytes_written),
            ("seq", result.seq),
            ("via", "presigned URL" if result.redirected_to else "API"),
        ],
    )
