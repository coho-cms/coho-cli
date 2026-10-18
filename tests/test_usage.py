"""`coho project usage` and `coho account usage` (coho-data doc 41), against the fake BFF."""

from __future__ import annotations

import json

from coho_management_sdk.testing import ACCOUNT, PROJECT, FakeBff

from conftest import Run


def test_project_usage_shows_delivery_by_key_and_who_managed(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT)
    out, _ = run("project", "usage")
    assert "Marketing site: usage\n2026-10-18 10:00 to 13:00 UTC, by the hour\n" in out
    assert "revalidated (304)  30" in out
    # key-1 answered 330 requests over 30 distinct URLs: eleven a URL, so the hint shows.
    assert "key-1" in out and "11.0" in out and "If-None-Match" in out
    assert "no key" in out and "keyless" in out
    assert "project tokens  60" in out
    assert "stored      5.7 MB  (13 files)" in out
    req = bff.last()
    assert req.path == f"/api/v1/accounts/{ACCOUNT}/projects/{PROJECT}/usage"
    assert dict(req.args) == {"grain": "hour"}


def test_project_usage_json_is_the_report_as_sent(run: Run) -> None:
    run("use", "acme", PROJECT)
    body = json.loads(run("-o", "json", "project", "usage")[0])
    assert body["grain"] == "hour" and len(body["buckets"]) == 3
    assert {m["meter"] for m in body["meters"]} >= {"delivery.requests", "assets.egress_bytes"}


def test_project_usage_names_a_project_and_a_range(run: Run, bff: FakeBff) -> None:
    out, _ = run("project", "usage", "Marketing site", "--grain", "day", "--from", "2026-10-16")
    assert "2026-10-16 through 2026-10-18 UTC, by the day" in out
    assert dict(bff.last().args) == {"grain": "day", "from": "2026-10-16T00:00:00Z"}


def test_meter_narrows_the_report_to_its_series(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT)
    out, _ = run("project", "usage", "-m", "delivery.requests", "-m", "assets.stored_bytes")
    [req] = [r for r in bff.requests if r.path.endswith("/usage")]
    assert req.args["meter"] == "delivery.requests,assets.stored_bytes"
    assert "delivery.requests" in out and "342 requests" in out
    assert "300 requests" in out and "key=key-1" in out  # each series, under its meter
    assert "assets.stored_bytes" in out and "Management" not in out


def test_periods_adds_a_line_per_bucket(run: Run) -> None:
    run("use", "acme", PROJECT)
    out, _ = run("project", "usage", "--periods")
    assert "By hour (UTC)" in out
    assert "2026-10-18 10:00" in out and "2026-10-18 12:00" in out


def test_a_grain_the_server_has_not_is_a_usage_error(run: Run) -> None:
    run("use", "acme", PROJECT)
    _, err = run("project", "usage", "--grain", "week", expect=2)
    assert "--grain must be" in err


def test_account_usage_sums_projects_for_an_admin(run: Run, bff: FakeBff) -> None:
    out, _ = run("account", "usage")
    assert "Acme: usage across projects" in out
    assert "delivery requests    342" in out
    assert "Marketing site  342" in out
    assert bff.last().path == f"/api/v1/accounts/{ACCOUNT}/projects/usage"

    body = json.loads(run("-o", "json", "account", "usage", "--grain", "day")[0])
    assert body["grain"] == "day" and body["projects"][0]["id"] == PROJECT


def test_account_usage_tells_a_member_where_to_look_instead(run: Run, bff: FakeBff) -> None:
    bff.account_admin = False
    out, err = run("account", "usage", expect=1)
    assert out == ""
    assert "FORBIDDEN" in err and "permission: account:admin" in err
    assert "coho project usage <project>" in err
