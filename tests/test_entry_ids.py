"""`@<slug>` for an entry id: looked up on the same ref through the live by-slug read."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest
from coho_management_sdk.testing import ACCOUNT, ENTRY, PROJECT, FakeBff, ok, problem
from werkzeug import Request, Response

from conftest import Run

PREVIEW = f"/api/v1/accounts/{ACCOUNT}/projects/{PROJECT}/preview"


def by_slug(bff: FakeBff, ref: str, slug: str, response: Response) -> list[Request]:
    """Answer the by-slug read for ``slug`` on ``ref``; return the requests it saw."""
    seen: list[Request] = []

    def handler(request: Request) -> Response:
        seen.append(request)
        return response

    bff.server.expect_request(
        f"{PREVIEW}/{ref}/entries-by-slug/{slug}", method="GET"
    ).respond_with_handler(handler)
    return seen


def graph(node: dict[str, Any]) -> Response:
    """The delivery envelope for one root at depth 0."""
    return ok({"roots": [node["id"]], "entries": {node["id"]: node}, "unresolved": {}})


HELLO: dict[str, Any] = {
    "id": ENTRY,
    "slug": "hello",
    "type": "blogPost",
    "locale": None,
    "fields": {},
}


def words(text: str) -> str:
    """The text with every run of whitespace as one space: Rich wraps errors at 80 columns."""
    return " ".join(text.split())


def slug_reads(bff: FakeBff) -> list[str]:
    return [r.path for r, _ in bff.server.log if "/entries-by-slug/" in r.path]


def test_entry_put_takes_a_slug_and_writes_the_entry_it_names(run: Run, bff: FakeBff) -> None:
    seen = by_slug(bff, "dev", "hello", graph(HELLO))
    run("use", "acme", PROJECT, "dev")
    out, _ = run("-o", "json", "entry", "put", "@hello", "--set", "rank=7")
    body = json.loads(out)
    assert body["id"] == ENTRY and body["fields"]["rank"] == 7
    assert len(seen) == 1
    # The id the slug named is the one written, with the ETag read from it.
    assert bff.last().method == "PUT" and bff.last().path.endswith(f"/entries/{ENTRY}")
    assert bff.last().headers["If-Match"] == '"v1"'


def test_a_plain_id_is_used_as_given_with_no_lookup(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT, "dev")
    run("-o", "json", "entry", "put", ENTRY, "--set", "rank=7")
    assert slug_reads(bff) == []


def test_a_slug_nothing_has_is_not_found_exit_5(run: Run, bff: FakeBff) -> None:
    by_slug(
        bff, "dev", "nope", problem(404, "ENTRY_NOT_FOUND", "No entry with slug 'nope' on 'dev'")
    )
    run("use", "acme", PROJECT, "dev")
    _, err = run("entry", "put", "@nope", "--set", "rank=7", expect=5)
    assert "ENTRY_NOT_FOUND" in words(err) and "no entry with slug 'nope' on dev" in words(err)
    assert "coho entry list" in words(err)
    assert not any(r.method == "PUT" for r, _ in bff.server.log)


def test_a_miss_the_bff_reports_as_route_not_found_is_still_a_missing_slug(
    run: Run, bff: FakeBff
) -> None:
    # The BFF's status page turns any 404 it relays into ROUTE_NOT_FOUND, for now.
    by_slug(bff, "dev", "nope", problem(404, "ROUTE_NOT_FOUND", "No such endpoint"))
    run("use", "acme", PROJECT, "dev")
    _, err = run("entry", "put", "@nope", "--set", "rank=7", expect=5)
    assert "no entry with slug 'nope' on dev" in words(err)
    assert "On a tag, slugs do not resolve" in words(err)


def test_an_id_typed_with_an_at_sign_is_a_slug_and_the_miss_says_to_drop_it(
    run: Run, bff: FakeBff
) -> None:
    by_slug(bff, "dev", ENTRY, problem(404, "ENTRY_NOT_FOUND", "no such slug"))
    run("use", "acme", PROJECT, "dev")
    _, err = run("entry", "get", f"@{ENTRY}", expect=5)
    assert "drop the `@`" in words(err)


def test_a_type_or_asset_slug_is_refused_as_not_an_entry(run: Run, bff: FakeBff) -> None:
    # Slugs are unique across types, entries and assets: the read finds the type.
    node = {"id": "44444444-4444-4444-8444-444444444444", "slug": "faq", "type": None}
    by_slug(bff, "dev", "faq", graph(node | {"fields": {}}))
    run("use", "acme", PROJECT, "dev")
    _, err = run("entry", "get", "@faq", expect=2)
    assert "not an entry" in words(err)


def test_a_slug_on_a_tag_says_to_use_the_id(run: Run, bff: FakeBff) -> None:
    # Live reads serve branches; a tag is refused as a ref that does not exist.
    by_slug(bff, "v1.0.0", "hello", problem(404, "REF_NOT_FOUND", "No such ref 'v1.0.0'"))
    run("use", "acme", PROJECT, "dev")
    _, err = run("--ref", "v1.0.0", "entry", "history", "@hello", expect=2)
    assert "tag" in words(err) and "Use the entry id" in words(err)


def test_an_at_sign_before_something_that_is_not_a_slug_is_a_usage_error(
    run: Run, bff: FakeBff
) -> None:
    run("use", "acme", PROJECT, "dev")
    for raw in ("@", "@Hello", "@a--b", "@hello_world"):
        _, err = run("entry", "get", raw, expect=2)
        assert "is not an entry slug" in words(err) and "without the `@`" in words(err)
    assert slug_reads(bff) == []


def test_every_entry_command_and_preview_entry_take_a_slug(run: Run, bff: FakeBff) -> None:
    seen = by_slug(bff, "dev", "hello", graph(HELLO))
    bff.server.expect_request(f"{PREVIEW}/dev/entries/{ENTRY}", method="GET").respond_with_json(
        {"roots": [ENTRY], "entries": {ENTRY: HELLO}, "unresolved": {}}
    )
    run("use", "acme", PROJECT, "dev")
    out, _ = run("-o", "json", "entry", "get", "@hello")
    assert json.loads(out)["id"] == ENTRY
    out, _ = run("-o", "json", "entry", "history", "@hello")
    assert json.loads(out)["id"] == ENTRY
    out, _ = run("-o", "json", "entry", "references", "@hello")
    assert json.loads(out)["id"] == ENTRY
    out, _ = run("preview", "entry", "@hello")
    assert json.loads(out)["roots"] == [ENTRY]
    out, _ = run("-y", "-o", "json", "entry", "delete", "@hello")
    assert json.loads(out)["id"] == ENTRY
    assert len(seen) == 5


def test_delete_asks_about_the_slug_and_the_id_it_found(
    run: Run, bff: FakeBff, monkeypatch: pytest.MonkeyPatch
) -> None:
    by_slug(bff, "dev", "hello", graph(HELLO))
    run("use", "acme", PROJECT, "dev")
    monkeypatch.setattr("sys.stdin", io.StringIO("n\n"))
    out, _ = run("entry", "delete", "@hello", expect=1)
    assert f"Delete entry @hello ({ENTRY}) on dev?" in out


# --- @<slug> in a reference field's --set value ---------------------------------------

REFS = f"/api/v1/accounts/{ACCOUNT}/projects/{PROJECT}/refs/dev"
PRIYA = "01920000-0000-7000-8000-0000000000a1"
TRAFFIC = "01920000-0000-7000-8000-0000000000b1"
DRAINAGE = "01920000-0000-7000-8000-0000000000b2"


def blog_post_type(bff: FakeBff) -> None:
    """A blogPost whose author and tags are references, and whose bio is text."""
    bff.server.expect_oneshot_request(f"{REFS}/types/blogPost", method="GET").respond_with_json(
        {
            "slug": "blogPost",
            "version": "t1",
            "definition": {
                "_name": "Blog post",
                "fields": [
                    {"id": "title", "type": "text"},
                    {"id": "bio", "type": "text"},
                    {"id": "author", "type": "reference", "of": ["teamMember"]},
                    {"id": "tags", "type": "reference", "of": ["tag"], "many": True},
                ],
            },
        }
    )


def node(id_: str, slug: str, type_: str) -> dict[str, Any]:
    return {"id": id_, "slug": slug, "type": type_, "locale": None, "fields": {}}


def type_reads(bff: FakeBff) -> list[str]:
    return [r.path for r, _ in bff.server.log if "/types/" in r.path]


def test_a_reference_set_to_a_slug_is_written_as_the_id_it_names(run: Run, bff: FakeBff) -> None:
    blog_post_type(bff)
    by_slug(bff, "dev", "priya-shah", graph(node(PRIYA, "priya-shah", "teamMember")))
    traffic = by_slug(bff, "dev", "traffic", graph(node(TRAFFIC, "traffic", "tag")))
    by_slug(bff, "dev", "drainage", graph(node(DRAINAGE, "drainage", "tag")))
    run("use", "acme", PROJECT, "dev")
    run(
        "-o", "json", "entry", "put", ENTRY,
        "--set", "author=@priya-shah",
        "--set", 'tags=["@traffic","@drainage","@traffic"]',
        "--set", "bio=@not-a-reference",
    )  # fmt: skip
    written = bff.last().get_json()["fields"]
    assert written["author"] == PRIYA
    assert written["tags"] == [TRAFFIC, DRAINAGE, TRAFFIC]
    # Only reference fields are looked up: a text field keeps its @ as typed.
    assert written["bio"] == "@not-a-reference"
    assert len(traffic) == 1  # each slug once, however often it is named


def test_create_takes_a_slug_in_a_reference_field(run: Run, bff: FakeBff) -> None:
    blog_post_type(bff)
    by_slug(bff, "dev", "priya-shah", graph(node(PRIYA, "priya-shah", "teamMember")))
    run("use", "acme", PROJECT, "dev")
    run(
        "entry",
        "create",
        "-t",
        "blogPost",
        "-s",
        "hi",
        "--set",
        "title=Hi",
        "--set",
        "author=@priya-shah",
    )
    assert bff.last().method == "POST" and bff.last().get_json()["fields"]["author"] == PRIYA


def test_sets_with_no_slug_read_no_type_and_look_nothing_up(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT, "dev")
    run("-o", "json", "entry", "put", ENTRY, "--set", f"author={PRIYA}", "--set", "rank=7")
    assert type_reads(bff) == [] and slug_reads(bff) == []


def test_a_reference_slug_nothing_has_is_not_found_and_nothing_is_written(
    run: Run, bff: FakeBff
) -> None:
    blog_post_type(bff)
    by_slug(bff, "dev", "nobody", problem(404, "ENTRY_NOT_FOUND", "no such slug"))
    run("use", "acme", PROJECT, "dev")
    _, err = run("entry", "put", ENTRY, "--set", "author=@nobody", expect=5)
    assert "no entry with slug 'nobody' on dev" in words(err)
    assert not any(r.method == "PUT" for r, _ in bff.server.log)


def test_put_with_a_file_reads_the_entry_type_to_find_its_references(
    run: Run, bff: FakeBff, tmp_path: Any
) -> None:
    blog_post_type(bff)
    by_slug(bff, "dev", "priya-shah", graph(node(PRIYA, "priya-shah", "teamMember")))
    doc = tmp_path / "post.json"
    doc.write_text(json.dumps({"title": "Hello"}))
    run("use", "acme", PROJECT, "dev")
    run("entry", "put", ENTRY, "--file", str(doc), "--set", "author=@priya-shah", "--force")
    assert bff.last().method == "PUT" and bff.last().get_json()["fields"]["author"] == PRIYA
