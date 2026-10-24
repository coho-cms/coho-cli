"""`coho` writes UTF-8 even when the locale would not: redirected output on Windows is in
cp1252, which has no box drawing, and used to end in a UnicodeEncodeError.

These run the real entry point in a subprocess, because the encoding a stream starts with
is decided when Python starts, which no in-process runner reproduces.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from coho_management_sdk.testing import PROJECT


def coho(*args: str, encoding: str) -> subprocess.CompletedProcess[bytes]:
    env = {
        **os.environ,
        # What Windows gives a pipe: its ANSI code page, not UTF-8.
        "PYTHONIOENCODING": encoding,
        "PYTHONUTF8": "0",
        "COLUMNS": "100",
    }
    env.pop("FORCE_COLOR", None)
    return subprocess.run(
        [sys.executable, "-m", "coho_cli.main", *args], capture_output=True, env=env, timeout=60
    )


@pytest.mark.parametrize("encoding", ["cp1252", "latin-1", "ascii"])
def test_help_survives_a_non_utf8_stdout(home: Path, encoding: str) -> None:
    done = coho("--help", encoding=encoding)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    # Box drawing, in UTF-8: rounded corners, or square ones where rich takes the
    # Windows console for a legacy one.
    help_text = done.stdout.decode("utf-8")
    assert "╭" in help_text or "┌" in help_text


def test_a_secret_is_still_alone_on_stdout(home: Path) -> None:
    assert coho("use", "acme", PROJECT, encoding="cp1252").returncode == 0
    done = coho("key", "create", "--label", "site", "--ref", "prod", encoding="cp1252")
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    # The secret's line is written byte for byte: nothing re-encoded, nothing replaced.
    # Windows ends lines with \r\n.
    assert done.stdout.decode("utf-8").replace("\r\n", "\n").endswith("\ncoho_dk_SECRET\n")
    assert "shown once" in done.stderr.decode("utf-8")
