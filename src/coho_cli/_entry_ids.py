"""``@<slug>`` wherever a command takes an entry id: the slug is looked up on the same
ref, and the command carries on with the id as if it had been typed.

The lookup is the delivery contract's ``entries-by-slug/{slug}`` read, which the BFF
serves live for a ref under ``preview/`` — one request at depth 0, the entry alone. The
management API has no slug filter on ``entries``, and paging through every entry to find
one is not a lookup.

What that read can and cannot answer:

- Slugs are unique per ref among every node's slugs (coho-data D24), so a slug names at
  most one node. That node may be a content type or an asset rather than an entry, and
  is refused as one.
- A deleted entry has no slug on the ref any more: its id still reaches its history.
- Live reads serve a branch, or an environment on one. A tag is refused as a ref that
  does not exist, so on a tag the id is the only way in.

Entry ids are UUIDs, so no id starts with ``@`` and the prefix cannot shadow one. A UUID
is a well-formed slug too, so ``@<uuid>`` is looked up as a slug like any other.

The same goes for the value of a reference field in ``--set``: ``author=@priya-shah``,
``tags=["@traffic","@drainage"]``. Only reference fields, as the entry's content type
declares them, are looked up, so a text field may still hold ``@handle``. The server
then checks the ids as it checks any: that each exists and is of a type the field allows.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

from coho_management_sdk import NotFound, Ref
from coho_management_sdk.errors import RefNotFound
from coho_management_sdk.transport import segment

from ._state import Usage

# A content slug, as `_slugs.content_slug` makes them and the server checks them.
_CONTENT_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def entry_id(ref: Ref, raw: str) -> str:
    """The entry id ``raw`` names on ``ref``: itself, or for ``@<slug>`` the id of the
    entry with that slug. Pass the ``Ref`` the command then acts on, so the slug is
    looked up where the id will be used."""
    if not raw.startswith("@"):
        return raw
    slug = raw[1:]
    if not _CONTENT_SLUG.match(slug):
        raise Usage(
            f"{raw!r} is not an entry slug: after `@` comes a slug such as @hello-world. "
            "An entry id is a UUID and is passed without the `@`."
        )
    preview = ref.preview()
    try:
        # ⚠️ The SDK's Preview has no by-slug read yet; this is the one request it would
        # make. Move it to `preview.entry_by_slug(slug)` once the SDK has one.
        body = preview._t.get(f"{preview.path}/entries-by-slug/{segment(slug)}").body or {}
    except RefNotFound:
        raise Usage(
            f"cannot look up {raw} on {ref.name}: slugs resolve on a branch, or an "
            "environment on one, and this ref is a tag or does not exist. Use the entry id."
        ) from None
    except NotFound as exc:
        # ⚠️ The BFF answers every 404 it relays as ROUTE_NOT_FOUND for now, its own
        # status page replacing authoring's problem, so a missing slug and a tag both
        # arrive as that. Read as either until the BFF relays the code it is given.
        if exc.code not in ("ENTRY_NOT_FOUND", "ROUTE_NOT_FOUND"):
            raise
        # A UUID is a well-formed slug too, so `@<id>` is looked up rather than refused.
        hint = (
            f"To use {slug} as an entry id, drop the `@`."
            if _is_uuid(slug)
            else "`coho entry list` shows the slugs."
        )
        if exc.code == "ROUTE_NOT_FOUND":
            hint += " On a tag, slugs do not resolve: use the entry id."
        raise NotFound(
            f"no entry with slug '{slug}' on {ref.name}. {hint}",
            code="ENTRY_NOT_FOUND",
            status=404,
        ) from None
    roots = body.get("roots") or []
    if len(roots) != 1:  # pragma: no cover - slugs are unique per ref (D24)
        raise Usage(f"{raw} names {len(roots)} nodes on {ref.name}. Use the entry id.")
    node = (body.get("entries") or {}).get(roots[0]) or {}
    # Only an entry has a content type. A type's or an asset's slug comes back without one.
    if not node.get("type"):
        raise Usage(
            f"{raw} on {ref.name} is a content type or an asset, not an entry. "
            "Slugs are unique across all three."
        )
    return str(roots[0])


def reference_ids(
    ref: Ref, type_of: Callable[[], str], sets: list[tuple[str, Any]]
) -> list[tuple[str, Any]]:
    """``--set`` values, each ``@<slug>`` in a reference field replaced by the entry id it
    names on ``ref``. ``type_of`` gives the entry's content type, and is only called, and
    the type only read, when some value names a slug: otherwise nothing is requested."""
    if not any(_names_slug(value) for _, value in sets):
        return sets
    links = {
        f.get("id")
        for f in ref.types.get(type_of()).fields
        if isinstance(f, dict) and f.get("type") == "reference"
    }
    found: dict[str, str] = {}

    def resolve(value: Any) -> Any:
        if not (isinstance(value, str) and value.startswith("@")):
            return value
        if value not in found:
            found[value] = entry_id(ref, value)
        return found[value]

    out: list[tuple[str, Any]] = []
    for path, value in sets:
        if path.split(".")[0] in links:
            value = [resolve(v) for v in value] if isinstance(value, list) else resolve(value)
        out.append((path, value))
    return out


def _names_slug(value: Any) -> bool:
    values = value if isinstance(value, list) else [value]
    return any(isinstance(v, str) and v.startswith("@") for v in values)


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True
