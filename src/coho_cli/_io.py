"""Reading JSON from files, stdin or inline strings — for --file and --fields."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from ._state import Usage


def read_json(source: str | None, *, what: str = "JSON") -> Any:
    """``-`` reads stdin; a path reads a file; anything starting with ``{`` or ``[`` is inline."""
    if source is None:
        raise Usage(f"{what} is required")
    text: str
    if source == "-":
        text = sys.stdin.read()
    elif source.lstrip().startswith(("{", "[")):
        text = source
    else:
        path = Path(source)
        if not path.exists():
            raise Usage(f"{what}: no such file: {source}")
        text = path.read_text()
    try:
        return json.loads(text)
    except ValueError as exc:
        raise Usage(f"{what} is not valid JSON: {exc}") from exc


def set_path(doc: dict[str, Any], dotted: str, value: Any) -> None:
    """Set ``a.b.c`` in a nested dict, creating levels. Used by ``--set``."""
    parts = dotted.split(".")
    cur = doc
    for p in parts[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[parts[-1]] = value


def parse_set(spec: str) -> tuple[str, Any]:
    """``path=value``; the value is JSON if it parses, else a string."""
    if "=" not in spec:
        raise Usage(f"--set needs path=value, got '{spec}'")
    path, raw = spec.split("=", 1)
    try:
        value: Any = json.loads(raw)
    except ValueError:
        value = raw
    return path.strip(), value
