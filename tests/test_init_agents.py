"""`coho init --agents`: COHO.md from the live project, and the pointers to it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from coho_management_sdk.testing import ACCOUNT, PROJECT, FakeBff

from coho_cli import _agents
from conftest import Run


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """The repository to write into: apart from `tmp_path`, where the CLI keeps its config."""
    path = tmp_path / "repo"
    path.mkdir()
    return path


def _init(run: Run, where: Path, *args: str, expect: int = 0) -> tuple[str, str]:
    return run("init", "--agents", "--dir", str(where), "--ref", "dev", *args, expect=expect)


def test_bare_init_says_what_it_can_write(run: Run) -> None:
    _, err = run("init", expect=2)
    assert "--agents" in err


def test_coho_md_describes_the_project_and_both_pointers_are_created(run: Run, repo: Path) -> None:
    run("use", "acme", PROJECT)
    out, _ = _init(run, repo)
    assert "Created COHO.md" in out and "Created AGENTS.md" in out and "Created CLAUDE.md" in out

    coho = (repo / "COHO.md").read_text()
    # The ids, recorded so the next run is the same project on any machine.
    assert coho.startswith('<!-- coho-agents: {"url": ')
    assert f'"account": "{ACCOUNT}", "project": "{PROJECT}", "ref": "dev"' in coho
    assert "# Marketing site: content in Coho" in coho
    # The model: the type, its field, required and localized; the locale entries use.
    assert "### `blogPost`: Blog post" in coho
    assert "- `title`: text, required, localized" in coho
    assert "In use: `en-US`, read from all 5 entries" in coho
    # The refs and where the environments point.
    assert "| `dev` |" in coho and "`v0.0.x`" in coho
    # The invariants.
    for rule in (
        "Use `-o json`",
        "Read before you write",
        "--if-match",
        "Exit code 4 means re-read",
        "Never merge, tag, promote or roll back",
    ):
        assert rule in coho, rule
    assert 'coho -o json --ref NAME entry put ID --set title.en-US="…"' in coho
    # Nobody is named: a person's credential is theirs, not the repository's.
    assert "ada@acme.example" not in coho

    agents = (repo / "AGENTS.md").read_text()
    assert agents.startswith(_agents.START) and "@COHO.md" in agents
    assert (repo / "CLAUDE.md").read_text() == "@AGENTS.md\n"


def test_running_again_changes_nothing_and_check_agrees(run: Run, repo: Path) -> None:
    run("use", "acme", PROJECT)
    _init(run, repo)
    before = {p.name: p.read_text() for p in repo.iterdir()}
    out, _ = _init(run, repo)
    assert "Created" not in out and "Updated" not in out
    assert {p.name: p.read_text() for p in repo.iterdir()} == before
    _init(run, repo, "--check")

    # A hand edit is drift: --check fails and names the file, and writes nothing.
    (repo / "COHO.md").write_text(before["COHO.md"] + "\nhand-written\n")
    _, err = _init(run, repo, "--check", expect=1)
    assert "out of date: COHO.md" in " ".join(err.split())
    assert "hand-written" in (repo / "COHO.md").read_text()


def test_the_block_merges_into_an_agents_md_without_touching_the_rest(run: Run, repo: Path) -> None:
    run("use", "acme", PROJECT)
    theirs = (
        "<!-- BEGIN:nextjs-agent-rules -->\r\n\r\n# Not the Next.js you know\r\n\r\n"
        "<!-- END:nextjs-agent-rules -->\r\n\r\nOur own notes.\r\n"
    )
    (repo / "AGENTS.md").write_bytes(theirs.encode())
    (repo / "CLAUDE.md").write_text("@AGENTS.md\n")
    out, _ = _init(run, repo)
    assert "Updated AGENTS.md" in out and "Unchanged CLAUDE.md" in out
    merged = (repo / "AGENTS.md").read_bytes().decode()
    assert merged.startswith(theirs)  # untouched, the other tool's block included
    assert _agents.START in merged and "\n" not in merged.replace("\r\n", "")  # CRLF kept

    # A stale block is replaced where it stands, not appended again.
    stale = merged.replace("Content lives in Coho", "An old heading")
    (repo / "AGENTS.md").write_bytes(stale.encode())
    _init(run, repo)
    assert (repo / "AGENTS.md").read_bytes().decode() == merged


def test_a_claude_md_on_its_own_takes_the_block_and_no_agents_md_appears(
    run: Run, repo: Path
) -> None:
    run("use", "acme", PROJECT)
    (repo / "CLAUDE.md").write_text("# House rules\n\nBe brief.\n")
    _init(run, repo)
    claude = (repo / "CLAUDE.md").read_text()
    assert claude.startswith("# House rules\n\nBe brief.\n\n" + _agents.START)
    assert not (repo / "AGENTS.md").exists()


def test_an_agents_md_that_claude_md_does_not_import_is_pointed_at_from_both(
    run: Run, repo: Path
) -> None:
    run("use", "acme", PROJECT)
    (repo / "AGENTS.md").write_text("For every agent.\n")
    (repo / "CLAUDE.md").write_text("For Claude only.\n")
    _init(run, repo)
    assert _agents.START in (repo / "AGENTS.md").read_text()
    assert _agents.START in (repo / "CLAUDE.md").read_text()


def test_the_project_comes_from_coho_md_then_codegen_config_then_the_context(
    run: Run, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Nothing saved, but @coho-cms/codegen's config names the project.
    (repo / "coho.config.json").write_text(
        json.dumps({"url": "https://ignored.example", "account": ACCOUNT, "project": PROJECT})
    )
    _, err = _init(run, repo)
    assert "Marketing site" in (repo / "COHO.md").read_text()
    assert "this profile reaches" in " ".join(err.split())  # its url is not this profile's

    # Once COHO.md exists, it names the project, whatever the config or context say.
    (repo / "coho.config.json").unlink()
    recorded = _agents.recorded_source(repo)
    assert recorded is not None and (recorded.account, recorded.project) == (ACCOUNT, PROJECT)
    _init(run, repo, "--check")


def test_with_no_project_anywhere_it_asks_for_one(run: Run, repo: Path) -> None:
    _, err = _init(run, repo, expect=2)
    assert "no project in context" in err


def test_a_project_token_records_its_role_but_never_a_person(
    run: Run, bff: FakeBff, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coho_management_sdk.testing import PROJECT_TOKEN

    monkeypatch.delenv("COHO_ACCESS_TOKEN")
    monkeypatch.setenv("COHO_TOKEN", PROJECT_TOKEN)
    run(
        "--account",
        ACCOUNT,
        "--project",
        PROJECT,
        "init",
        "--agents",
        "--dir",
        str(repo),
        "--ref",
        "dev",
    )
    coho = (repo / "COHO.md").read_text()
    assert 'project token "CI deploy", role `author`' in coho
    assert "`content:write`" in coho and "Acme" in coho


def test_upsert_appends_after_a_blank_line_and_replaces_in_place() -> None:
    block = _agents.block()
    assert _agents.upsert("", block) == block + "\n"
    assert _agents.upsert("Notes.", block) == "Notes.\n\n" + block + "\n"
    once = _agents.upsert("Notes.\n", block)
    assert once == "Notes.\n\n" + block + "\n"
    assert _agents.upsert(once, block) == once
