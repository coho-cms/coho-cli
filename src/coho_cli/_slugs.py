"""Build slugs from names. The API checks them; this is the one place they are made.

A type slug is camelCase (``Blog post`` -> ``blogPost``) because it appears in code:
``coho entry create -t blogPost`` and ``of: ["teamMember"]``. A content slug is
kebab-case (``Hello, World!`` -> ``hello-world``) because it appears in URLs.

These rules mirror ``coho.model.Slugs`` on the server, which stays the authority: a
generated slug that the server would refuse is refused here first, with a message
that says what to pass instead.
"""

from __future__ import annotations

import re
import unicodedata

from ._state import Usage

_TYPE_SLUG = re.compile(r"^[a-z][a-zA-Z0-9]*$")
_CONTENT_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _words(name: str) -> list[str]:
    # Accents fold to their base letter (Über -> Uber). Anything else that is not
    # ASCII letter or digit is a separator, so punctuation and spacing both break words.
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.findall(r"[A-Za-z0-9]+", folded)


def type_slug(name: str) -> str:
    """camelCase from a name: the first word lowercased, each later word capitalised."""
    words = _words(name)
    if not words:
        raise Usage(
            f"cannot build a type slug from {name!r}: it has no letters or digits. "
            "Pass the slug explicitly."
        )
    head, *tail = words
    slug = head.lower() + "".join(w[:1].upper() + w[1:].lower() for w in tail)
    if not _TYPE_SLUG.match(slug):
        raise Usage(
            f"cannot build a type slug from {name!r}: it must start with a letter. "
            "Pass the slug explicitly."
        )
    return slug


def content_slug(name: str) -> str:
    """kebab-case from a name: every word lowercased and joined with hyphens."""
    words = _words(name)
    if not words:
        raise Usage(
            f"cannot build a content slug from {name!r}: it has no letters or digits. "
            "Pass --slug explicitly."
        )
    slug = "-".join(w.lower() for w in words)
    if not _CONTENT_SLUG.match(slug):  # pragma: no cover - the rule holds by construction
        raise Usage(f"cannot build a content slug from {name!r}. Pass --slug explicitly.")
    return slug
