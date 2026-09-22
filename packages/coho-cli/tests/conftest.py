"""CLI tests run the real command tree against the SDK's fake BFF."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pytest_httpserver import HTTPServer

from coho_sdk.testing import FakeBff


@pytest.fixture
def bff(httpserver: HTTPServer) -> FakeBff:
    return FakeBff(httpserver)


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bff: FakeBff) -> Path:
    """An isolated config dir with one profile pointed at the fake BFF and a token in the env."""
    cfg = tmp_path / "cfg"
    monkeypatch.setenv("COHO_CONFIG_DIR", str(cfg))
    monkeypatch.setenv("COHO_ACCESS_TOKEN", "test-token")
    monkeypatch.delenv("COHO_PROFILE", raising=False)
    monkeypatch.delenv("COHO_ACCOUNT", raising=False)
    monkeypatch.delenv("COHO_PROJECT", raising=False)
    monkeypatch.delenv("COHO_REF", raising=False)
    from coho_sdk.profiles import Config

    c = Config(path=cfg / "config.toml")
    p = c.profile("test", create=True)
    p.url = bff.url
    p.token_store = "file"
    c.current_profile = "test"
    c.save()
    return cfg


class Run:
    def __init__(self, capsys: pytest.CaptureFixture[str]) -> None:
        self.capsys = capsys

    def __call__(self, *args: str, expect: int = 0) -> tuple[str, str]:
        """Run ``coho <args>`` through the real entry point; return (stdout, stderr)."""
        import coho_cli.main as main

        old = sys.argv
        sys.argv = ["coho", *args]
        code = 0
        try:
            main.main()
        except SystemExit as exc:
            code = int(exc.code or 0)
        finally:
            sys.argv = old
        out, err = self.capsys.readouterr()
        assert code == expect, f"exit {code} != {expect}\nstdout:\n{out}\nstderr:\n{err}"
        return out, err


@pytest.fixture
def run(capsys: pytest.CaptureFixture[str], home: Path) -> Run:
    return Run(capsys)
