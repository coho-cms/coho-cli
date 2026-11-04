"""Whether this machine has a browser to open, and opening one or printing the URL instead.

coho-data doc 73 HL-7: a person on an SSH session or a headless server should not have to
know `--no-browser`. Over SSH a browser opened here would appear on the remote machine's
screen, or nowhere; on Linux with no display there is nothing to open one on.
"""

from __future__ import annotations

import os
import sys
import webbrowser

from ._output import console


def no_browser_reason() -> str | None:
    """Why there is plainly no browser here, in a few words, or None when there may be one."""
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"):
        return "SSH session"
    if sys.platform.startswith("linux") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        return "no display"
    return None


def print_url(intro: str, url: str) -> None:
    console.print(f"{intro}\n", highlight=False)
    console.print(f"  {url}", markup=False, highlight=False, soft_wrap=True)
    console.print()


def open_or_print(url: str, *, print_instead: bool, intro: str) -> bool:
    """Open [url] here, or print it under [intro]. Printed too when the opening fails.

    Returns:
        True when a browser was opened here.
    """
    if not print_instead and webbrowser.open(url):
        return True
    print_url(intro, url)
    return False
