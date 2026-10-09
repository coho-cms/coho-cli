"""Slugs built from names: the pure rules, and the commands that build them."""

from __future__ import annotations

import json

import pytest
from coho_management_sdk.testing import PROJECT

from coho_cli._slugs import content_slug, type_slug
from coho_cli._state import Usage
from conftest import Run


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("Blog post", "blogPost"),
        ("Team member", "teamMember"),
        ("blog post", "blogPost"),
        ("BLOG POST", "blogPost"),
        ("SEO description", "seoDescription"),
        ("Reading time (minutes)", "readingTimeMinutes"),
        ("Über article", "uberArticle"),
        ("page2", "page2"),
        ("tag", "tag"),
    ],
)
def test_type_slugs_are_camel_case(name: str, slug: str) -> None:
    assert type_slug(name) == slug


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("Hello, World!", "hello-world"),
        ("hello_world", "hello-world"),
        ("  Post 2026 ", "post-2026"),
        ("FAQ", "faq"),
        ("Über uns", "uber-uns"),
        ("a--b", "a-b"),
    ],
)
def test_content_slugs_are_kebab_case(name: str, slug: str) -> None:
    assert content_slug(name) == slug


@pytest.mark.parametrize("name", ["", "   ", "!!!", "日本語"])
def test_a_name_with_nothing_to_build_from_is_refused(name: str) -> None:
    with pytest.raises(Usage, match="Pass"):
        content_slug(name)
    with pytest.raises(Usage, match="Pass"):
        type_slug(name)


def test_a_type_slug_must_start_with_a_letter() -> None:
    with pytest.raises(Usage, match="must start with a letter"):
        type_slug("2026 plan")


def test_entry_create_builds_the_slug_from_name(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")
    out, _ = run(
        "-o",
        "json",
        "entry",
        "create",
        "-t",
        "blogPost",
        "-f",
        '{"_name": "Hello, World!", "title": {"en-US": "Hi"}}',
    )
    assert json.loads(out)["slug"] == "hello-world"


def test_entry_create_with_no_name_and_no_slug_says_what_to_pass(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")
    _, err = run("entry", "create", "-t", "blogPost", "--set", "rank=1", expect=2)
    assert "--slug" in err and "_name" in err


def test_an_explicit_slug_is_still_sent_as_given(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")
    out, _ = run(
        "-o",
        "json",
        "entry",
        "create",
        "-t",
        "blogPost",
        "-s",
        "my-own-slug",
        "-f",
        '{"_name": "Hello, World!", "title": {"en-US": "Hi"}}',
    )
    assert json.loads(out)["slug"] == "my-own-slug"


def test_type_put_builds_the_slug_from_name_and_asks_before_updating(run: Run) -> None:
    # The fake BFF already has blogPost, so a derived "Blog post" is an update.
    run("use", "acme", PROJECT, "dev")
    _, err = run("type", "put", "-f", '{"_name": "Blog post", "fields": []}', expect=2)
    assert "--if-match" in err and "blogPost" in err

    out, _ = run(
        "-o",
        "json",
        "type",
        "put",
        "-f",
        '{"_name": "Blog post", "fields": []}',
        "--if-match",
        '"t1"',
    )
    assert json.loads(out)["slug"] == "blogPost"


def test_type_put_creates_a_new_type_from_its_name(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")
    out, _ = run("-o", "json", "type", "put", "-f", '{"_name": "New type", "fields": []}')
    assert json.loads(out)["slug"] == "newType"


def test_type_put_with_no_name_and_no_slug_is_a_usage_error(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")
    _, err = run("type", "put", "-f", '{"fields": []}', expect=2)
    assert "_name" in err
