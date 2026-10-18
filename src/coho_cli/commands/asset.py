"""asset: upload, list, get, url, put, delete."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlencode

import typer
from coho_management_sdk.client import AssetsApi
from coho_management_sdk.models import Asset, FocalPoint

from .._output import console, emit_json, record, say, table, warn
from .._slugs import content_slug
from .._state import State, Usage, get_state

app = typer.Typer(
    help="Files on the current ref: images, PDF, audio and video. ⚠️ Public to anyone with the URL.",
    no_args_is_help=True,
)

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

_PUBLIC = (
    "asset URLs are public to anyone holding them, drafts included, and keep working after "
    "a delete. Upload nothing that must stay private."
)


@app.command("upload")
def upload(
    ctx: typer.Context,
    files: Annotated[list[Path], typer.Argument(help="One or more files.", show_default=False)],
    slug: Annotated[
        str | None,
        typer.Option(
            "--slug",
            "-s",
            help="The asset's slug. One file only; omit it to build one from the filename.",
        ),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Its human name.")] = None,
    alt: Annotated[str | None, typer.Option("--alt", help="Alternative text for images.")] = None,
    focal: Annotated[
        str | None,
        typer.Option("--focal", help="Where crops centre, as x,y fractions: --focal 0.5,0.3."),
    ] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag", help="A tag; repeat for more.")] = None,
) -> None:
    """Upload files as assets on the current branch.

    Each file is hashed, sent straight to object storage on a presigned URL (never
    through the API), and written as an asset. Bytes the project already holds are not
    sent again. With no --slug, the slug comes from the filename without its extension
    ("Hero Shot.jpg" -> hero-shot).
    """
    state = get_state(ctx)
    if slug is not None and len(files) > 1:
        raise Usage("--slug names one asset; give one file, or leave --slug out")
    for path in files:
        if not path.is_file():
            raise Usage(f"{path}: no such file")
        size = path.stat().st_size
        if size > AssetsApi.MAX_BYTES:
            raise Usage(f"{path}: {_size(size)} is over the {_size(AssetsApi.MAX_BYTES)} limit")
    focal_point = _focal(focal)
    if state.output != "json" and not state.quiet:
        warn(_PUBLIC)

    api = state.ref().assets
    uploaded: list[Asset] = []
    for path in files:
        asset = api.upload(
            path,
            slug=slug or _slug_for(path),
            title=title,
            alt=alt,
            focal_point=focal_point,
            tags=tag,
        )
        uploaded.append(asset)
        say(state, f"Uploaded {path.name} as {asset.slug}: {_describe(asset)}")
        if state.output != "json" and not state.quiet and asset.url:
            console.print(f"  {asset.url}", highlight=False, markup=False)

    if state.output == "json":
        if len(uploaded) == 1:
            emit_json(_json(uploaded[0]))
        else:
            emit_json({"assets": [_json(a) for a in uploaded]})


@app.command("list")
def list_(
    ctx: typer.Context,
    limit: Annotated[int, typer.Option("--limit", help="1..1000 per page.")] = 100,
    offset: Annotated[int, typer.Option("--offset")] = 0,
    all_: Annotated[bool, typer.Option("--all", help="Follow pages until the end.")] = False,
) -> None:
    """List assets in slug order (one page, or --all)."""
    state = get_state(ctx)
    api = state.ref().assets
    if all_:
        assets = list(api.iterate(page_size=limit))
        raw: Any = {"assets": [a.raw for a in assets]}
        more = False
    else:
        page = api.list(limit=limit, offset=offset)
        assets = page.assets
        raw = page.raw
        more = page.page.has_more
    table(
        state,
        raw,
        ["ID", "SLUG", "TYPE", "SIZE", "PIXELS", "TITLE"],
        [
            (a.id, a.slug, a.file.media_type, _size(a.file.byte_size), _pixels(a), a.title)
            for a in assets
        ],
    )
    if state.output != "json" and more:
        console.print(f"[dim]more: --offset {offset + len(assets)}, or --all[/dim]")


@app.command("get")
def get(
    ctx: typer.Context,
    asset: Annotated[str, typer.Argument(help="An asset id or slug.")],
) -> None:
    """One asset, with its URLs and ETag."""
    state = get_state(ctx)
    a = _resolve(state, asset)
    if state.output == "json":
        emit_json(_json(a))
        return
    record(
        state,
        a.raw,
        [
            ("id", a.id),
            ("slug", a.slug),
            ("title", a.title),
            ("alt", a.alt),
            ("file", a.file.filename),
            ("type", a.file.media_type),
            ("size", _size(a.file.byte_size)),
            ("pixels", _pixels(a)),
            ("focal", f"{a.focal_point.x},{a.focal_point.y}" if a.focal_point else None),
            ("tags", ", ".join(a.tags) or None),
            ("sha256", a.file.sha256),
            ("url", a.url),
            ("image url", a.image_url),
            ("version", a.version),
            ("etag", a.etag),
        ],
    )


@app.command("url")
def url(
    ctx: typer.Context,
    asset: Annotated[str, typer.Argument(help="An asset id or slug.")],
    width: Annotated[
        int | None, typer.Option("--width", "-w", help="Resize to this width.")
    ] = None,
    height: Annotated[int | None, typer.Option("--height", help="And/or height.")] = None,
    fit: Annotated[
        str | None, typer.Option("--fit", help="scale, pad, fill, crop or thumb.")
    ] = None,
    format_: Annotated[
        str | None, typer.Option("--format", help="auto, avif, webp, jpg or png.")
    ] = None,
    quality: Annotated[int | None, typer.Option("--quality", help="1..100.")] = None,
) -> None:
    """Print an asset's URL, resized on request when any size or format is given.

    A fill or crop centres on the asset's focal point. The edge rounds widths up to its
    fixed steps, so asking for 799 serves 828.
    """
    state = get_state(ctx)
    a = _resolve(state, asset)
    params: dict[str, Any] = {
        "w": width,
        "h": height,
        "fit": fit,
        "fm": format_,
        "q": quality,
    }
    if fit in ("fill", "crop", "thumb") and a.focal_point is not None:
        params["fx"], params["fy"] = a.focal_point.x, a.focal_point.y
    query = {k: v for k, v in params.items() if v is not None}
    if not query:
        link = a.url
    elif a.image_url is None:
        raise Usage(f"{a.slug} is {a.file.media_type}, which is served only as it was uploaded")
    else:
        link = f"{a.image_url}?{urlencode(query)}"
    if link is None:
        raise Usage("this deployment serves no asset URLs")
    if state.output == "json":
        emit_json({"id": a.id, "url": link})
    else:
        console.print(link, highlight=False, markup=False, soft_wrap=True)


@app.command("put")
def put(
    ctx: typer.Context,
    asset: Annotated[str, typer.Argument(help="An asset id or slug.")],
    title: Annotated[str | None, typer.Option("--title")] = None,
    alt: Annotated[str | None, typer.Option("--alt")] = None,
    focal: Annotated[str | None, typer.Option("--focal", help="x,y fractions.")] = None,
    tag: Annotated[
        list[str] | None, typer.Option("--tag", help="Replaces the tags; repeat for more.")
    ] = None,
    clear: Annotated[
        list[str] | None,
        typer.Option("--clear", help="Clear a field: title, alt, focal or tags. Repeatable."),
    ] = None,
) -> None:
    """Change an asset's metadata. The file itself never changes; upload a new one.

    Reads the asset, applies the changes, and writes it back with its own ETag, so it
    fails with VERSION_CONFLICT if somebody else wrote in between.
    """
    state = get_state(ctx)
    cleared = set(clear or [])
    unknown = cleared - {"title", "alt", "focal", "tags"}
    if unknown:
        raise Usage(f"--clear takes title, alt, focal or tags, not {', '.join(sorted(unknown))}")
    if title is None and alt is None and focal is None and tag is None and not cleared:
        raise Usage("nothing to change: pass --title, --alt, --focal, --tag or --clear")

    current = _resolve(state, asset)
    current.title = None if "title" in cleared else (title if title is not None else current.title)
    current.alt = None if "alt" in cleared else (alt if alt is not None else current.alt)
    current.focal_point = None if "focal" in cleared else (_focal(focal) or current.focal_point)
    current.tags = [] if "tags" in cleared else (list(tag) if tag is not None else current.tags)
    a = state.ref().assets.put(current)
    if state.output == "json":
        emit_json(_json(a))
    else:
        say(state, f"Updated {a.slug} ({a.etag}).")


@app.command("delete")
def delete(
    ctx: typer.Context,
    asset: Annotated[str, typer.Argument(help="An asset id or slug.")],
) -> None:
    """Tombstone an asset on this branch.

    ⚠️ The bytes stay and the URL keeps working: history and released tags still point at
    it, so a rollback finds its images.
    """
    state = get_state(ctx)
    a = _resolve(state, asset)
    if not state.yes and not typer.confirm(
        f"Delete asset {a.slug} on {state.context.ref}? Its URL will keep working."
    ):
        raise typer.Abort()
    etag = state.ref().assets.delete(a)
    if state.output == "json":
        emit_json({"id": a.id, "etag": etag})
    else:
        say(state, f"Deleted {a.slug} (tombstone {etag}).")


# -- helpers ---------------------------------------------------------------------


def _resolve(state: State, asset: str) -> Asset:
    """An asset by id, or by slug on the current ref."""
    api = state.ref().assets
    if _UUID.match(asset):
        return api.get(asset)
    for a in api.iterate(page_size=1000):
        if a.slug == asset:
            return api.get(a.id)
    raise Usage(f"no asset with slug {asset!r} on {state.context.ref}")


def _slug_for(path: Path) -> str:
    """kebab-case from the filename, without its extension: "Hero Shot.jpg" -> hero-shot."""
    try:
        return content_slug(path.stem)
    except Usage:
        raise Usage(f"cannot build a slug from {path.name!r}. Pass --slug.") from None


def _focal(value: str | None) -> FocalPoint | None:
    if value is None:
        return None
    try:
        x, y = (float(v) for v in value.split(","))
    except ValueError:
        raise Usage(f"--focal takes x,y as fractions, such as 0.5,0.3, not {value!r}") from None
    if not (0 <= x <= 1 and 0 <= y <= 1):
        raise Usage("--focal x and y must each be between 0 and 1")
    return FocalPoint(x, y)


def _json(a: Asset) -> dict[str, Any]:
    return a.raw | {"etag": a.etag}


def _describe(a: Asset) -> str:
    pixels = _pixels(a)
    return f"{a.file.media_type}, {_size(a.file.byte_size)}" + (f", {pixels}" if pixels else "")


def _pixels(a: Asset) -> str | None:
    if a.file.width is None or a.file.height is None:
        return None
    return f"{a.file.width}×{a.file.height}"


def _size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
