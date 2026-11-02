"""`coho pin`: the caller's pinned entries in the current project (coho-data doc 67)."""

from __future__ import annotations

import json

from coho_management_sdk.testing import ENTRY, PROJECT, FakeBff

from conftest import Run
from test_entry_ids import HELLO, by_slug, graph, words

OTHER = "66666666-6666-4666-8666-666666666666"


def test_pins_are_listed_top_first_as_they_read_on_the_ref(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT, "dev")
    out, _ = run("pin", "list")
    assert "(no pins)" in out
    run("pin", "add", OTHER)
    out, _ = run("pin", "add", ENTRY)
    assert f"Pinned {ENTRY}." in out
    out, _ = run("pin", "list")
    assert out.index("Hello") < out.index("not on this ref")
    assert bff.last().args["ref"] == "dev"
    out, _ = run("-o", "json", "pin", "list")
    assert [p["entryId"] for p in json.loads(out)["pins"]] == [ENTRY, OTHER]


def test_a_pin_takes_a_slug_resolved_on_the_current_ref(run: Run, bff: FakeBff) -> None:
    by_slug(bff, "dev", "hello", graph(HELLO))
    run("use", "acme", PROJECT, "dev")
    out, _ = run("pin", "add", "@hello")
    assert f"Pinned @hello ({ENTRY})." in out
    assert bff.pins == [ENTRY]


def test_the_order_names_every_pin_once(run: Run, bff: FakeBff) -> None:
    bff.pins = [ENTRY, OTHER]
    run("use", "acme", PROJECT, "dev")
    run("pin", "order", OTHER, ENTRY)
    assert bff.pins == [OTHER, ENTRY]
    _, err = run("pin", "order", OTHER, expect=1)
    assert "each pinned entry once" in err


def test_unpinning_what_is_not_pinned_is_not_an_error(run: Run, bff: FakeBff) -> None:
    bff.pins = [ENTRY]
    run("use", "acme", PROJECT, "dev")
    run("pin", "remove", ENTRY)
    out, _ = run("pin", "remove", ENTRY)
    assert f"Unpinned {ENTRY}." in out and bff.pins == []


def test_the_twenty_first_pin_is_refused_with_its_code(run: Run, bff: FakeBff) -> None:
    bff.pins = [f"00000000-0000-4000-8000-{i:012d}" for i in range(20)]
    run("use", "acme", PROJECT, "dev")
    _, err = run("pin", "add", ENTRY, expect=1)
    assert "PIN_LIMIT" in err and "Unpin one first" in words(err)
