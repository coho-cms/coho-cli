"""`--set-file path=FILE`: a `--set` value read from a file, for what no shell passes intact.

Windows PowerShell 5.1 drops the double quotes inside an argument, so a JSON list of
repeater items cannot be typed there, nor read in with `$(…)`.
"""

from __future__ import annotations

import json
from pathlib import Path

from coho_management_sdk.testing import ENTRY, PROJECT, FakeBff

from conftest import Run
from test_entry_ids import DRAINAGE, TRAFFIC, blog_post_type, by_slug, graph, node, words

CITATIONS = [
    {
        "authors": "Robinson, B. W., et al.",
        "year": 2000,
        "title": "Roundabouts: An informational guide",
    },
    {"authors": "Rodegerdts, L., et al.", "year": 2010, "title": "Roundabouts, 2nd ed."},
]


def test_put_sets_a_field_to_the_json_in_a_file(run: Run, bff: FakeBff, tmp_path: Path) -> None:
    file = tmp_path / "citations.json"
    file.write_text(json.dumps(CITATIONS, indent=2), encoding="utf-8")
    run("use", "acme", PROJECT, "dev")
    run("-o", "json", "entry", "put", ENTRY, "--set-file", f"citations={file}", "--set", "rank=3")
    written = bff.last().get_json()["fields"]
    assert written["citations"] == CITATIONS
    assert written["rank"] == 3


def test_a_file_is_read_as_utf8_with_or_without_a_byte_order_mark(
    run: Run, bff: FakeBff, tmp_path: Path
) -> None:
    # Windows PowerShell 5.1's Set-Content -Encoding UTF8 starts the file with a BOM.
    file = tmp_path / "title.json"
    file.write_bytes(
        b"\xef\xbb\xbf" + json.dumps({"en-US": "Brücke — final"}, ensure_ascii=False).encode()
    )
    run("use", "acme", PROJECT, "dev")
    run("-o", "json", "entry", "put", ENTRY, "--set-file", f"title={file}")
    assert bff.last().get_json()["fields"]["title"] == {"en-US": "Brücke — final"}


def test_a_file_that_is_not_json_is_its_text(run: Run, bff: FakeBff, tmp_path: Path) -> None:
    file = tmp_path / "body.md"
    file.write_text("# Notes\n\nRoads, rails and drains.\n", encoding="utf-8")
    run("use", "acme", PROJECT, "dev")
    run("-o", "json", "entry", "put", ENTRY, "--set-file", f"body.en-US={file}")
    assert bff.last().get_json()["fields"]["body"] == {
        "en-US": "# Notes\n\nRoads, rails and drains.\n"
    }


def test_slugs_in_a_file_are_looked_up_as_in_set(run: Run, bff: FakeBff, tmp_path: Path) -> None:
    blog_post_type(bff)
    by_slug(bff, "dev", "traffic", graph(node(TRAFFIC, "traffic", "tag")))
    by_slug(bff, "dev", "drainage", graph(node(DRAINAGE, "drainage", "tag")))
    file = tmp_path / "tags.json"
    file.write_text('["@traffic", "@drainage"]', encoding="utf-8")
    run("use", "acme", PROJECT, "dev")
    run("-o", "json", "entry", "put", ENTRY, "--set-file", f"tags={file}")
    assert bff.last().get_json()["fields"]["tags"] == [TRAFFIC, DRAINAGE]


def test_create_takes_set_file_too(run: Run, bff: FakeBff, tmp_path: Path) -> None:
    file = tmp_path / "citations.json"
    file.write_text(json.dumps(CITATIONS), encoding="utf-8")
    run("use", "acme", PROJECT, "dev")
    run(
        "-o", "json", "entry", "create", "-t", "note", "--slug", "n",
        "--set", "title=A note", "--set-file", f"citations={file}",
    )  # fmt: skip
    assert bff.last().get_json()["fields"]["citations"] == CITATIONS


def test_a_missing_file_writes_nothing(run: Run, bff: FakeBff, tmp_path: Path) -> None:
    run("use", "acme", PROJECT, "dev")
    _, err = run(
        "entry", "put", ENTRY, "--set-file", f"citations={tmp_path / 'none.json'}", expect=2
    )
    assert "no such file" in words(err)
    assert not [r for r, _ in bff.server.log if r.method == "PUT"]


def test_set_file_needs_a_path_and_a_file(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT, "dev")
    _, err = run("entry", "put", ENTRY, "--set-file", "citations.json", expect=2)
    assert "needs path=FILE" in words(err)


def test_file_reads_utf8_whatever_the_locale(run: Run, bff: FakeBff, tmp_path: Path) -> None:
    # `--file` too: it read in the locale's encoding, cp1252 on Windows, and a BOM failed.
    file = tmp_path / "fields.json"
    file.write_bytes(b"\xef\xbb\xbf" + json.dumps({"title": "Brücke"}, ensure_ascii=False).encode())
    run("use", "acme", PROJECT, "dev")
    run("-o", "json", "entry", "create", "-t", "note", "--slug", "n", "-f", str(file))
    assert bff.last().get_json()["fields"]["title"] == "Brücke"
