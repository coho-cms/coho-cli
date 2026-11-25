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
        # UTF-8 whatever the locale, as JSON is: Windows would read cp1252. A byte order
        # mark, which Windows PowerShell 5.1 writes, is skipped.
        text = path.read_text(encoding="utf-8-sig")
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


def parse_set_file(spec: str) -> tuple[str, Any]:
    """``path=FILE``: as ``--set``, with the value read from a UTF-8 file.

    For a value no shell passes intact, such as a JSON list of repeater items in Windows
    PowerShell 5.1, which drops the double quotes inside an argument.
    """
    if "=" not in spec:
        raise Usage(f"--set-file needs path=FILE, got '{spec}'")
    path, name = spec.split("=", 1)
    file = Path(name)
    if not file.is_file():
        raise Usage(f"--set-file {path.strip()}: no such file: {name}")
    try:
        raw = file.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise Usage(f"--set-file {path.strip()}: {name} is not UTF-8 text") from exc
    try:
        value: Any = json.loads(raw)
    except ValueError:
        value = raw
    return path.strip(), value
