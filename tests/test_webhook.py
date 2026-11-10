"""`coho webhook`: the endpoints Coho calls, and their log (coho-data doc 70)."""

from __future__ import annotations

import io
import json

import pytest
from coho_management_sdk.testing import PROJECT, FakeBff

from conftest import Run
from test_entry_ids import words


def _use(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")


def _create(run: Run, *args: str) -> str:
    out, _ = run("-o", "json", "webhook", "create", "--url", "https://hooks.example.com/", *args)
    return str(json.loads(out)["webhook"]["id"])


def test_create_prints_the_secret_once_with_a_warning(run: Run, bff: FakeBff) -> None:
    _use(run)
    out, err = run(
        "webhook",
        "create",
        "--url",
        "https://build.example.com/hooks/coho",
        "--event",
        "environment.promoted",
        "-e",
        "tag.*",
        "--ref",
        "prod",
        "--header",
        "Authorization: Bearer xyz",
        "--description",
        "Rebuild the site",
    )
    [webhook_id] = bff.webhooks
    secret = bff.webhook_secrets[webhook_id]
    assert f"\n{secret}\n" in out and "Signing secret" in out
    assert "shown once and cannot be retrieved again" in err
    assert bff.last().get_json() == {
        "url": "https://build.example.com/hooks/coho",
        "events": ["environment.promoted", "tag.*"],
        "enabled": True,
        "refs": ["prod"],
        "headers": {"Authorization": "Bearer xyz"},
        "description": "Rebuild the site",
    }
    assert bff.webhook_headers[webhook_id] == {"Authorization": "Bearer xyz"}


def test_create_disabled_and_for_every_ref(run: Run, bff: FakeBff) -> None:
    _use(run)
    webhook_id = _create(run, "--event", "*", "--disabled")
    body = bff.requests[-1].get_json()
    assert body["enabled"] is False and "refs" not in body
    out, _ = run("webhook", "show", webhook_id)
    assert "https://hooks.example.com/" in out and "(all)" in out and "disabled" in out


def test_a_header_must_be_name_colon_value(run: Run) -> None:
    _use(run)
    _, err = run(
        "webhook",
        "create",
        "--url",
        "https://x.example.com/",
        "-e",
        "*",
        "--header",
        "Nope",
        expect=2,
    )
    assert "'Name: value'" in err


def test_list_shows_host_state_and_health_but_not_the_url(run: Run, bff: FakeBff) -> None:
    _use(run)
    out, _ = run("webhook", "list")
    assert "(no webhooks)" in out
    webhook_id = _create(run, "-e", "*")
    bff.add_delivery(webhook_id, state="succeeded", status=200)
    bff.add_delivery(webhook_id, state="failed", status=503)
    out, _ = run("webhook", "list")
    # The id whole, to copy into the next command; at 80 columns the host wraps instead.
    assert webhook_id in out and "enabled" in out
    assert "1 ok, 1 failed" in words(out) and "1 of 25 webhooks." in out
    out, _ = run("-o", "json", "webhook", "list")
    doc = json.loads(out)
    assert doc["limit"] == 25 and "url" not in doc["webhooks"][0]
    assert doc["webhooks"][0]["host"] == "hooks.example.com"


def test_events_lists_types_and_groups_with_a_serial_comma(run: Run) -> None:
    _use(run)
    out, _ = run("webhook", "events")
    assert "environment.promoted" in out
    assert "tag.*, tag_request.*" in out and ", and webhook.*." in words(out)


def test_update_sends_what_changes(run: Run, bff: FakeBff) -> None:
    _use(run)
    webhook_id = _create(run, "-e", "*", "--ref", "main", "--header", "X-Team: web")
    out, _ = run("webhook", "update", webhook_id, "--all-refs", "--clear-headers", "--disable")
    assert bff.last().get_json() == {"refs": [], "headers": {}, "enabled": False}
    assert "(all)" in out and "disabled" in out
    run("webhook", "update", webhook_id, "--enable", "-e", "tag.ready", "--description", "")
    assert bff.last().get_json() == {"events": ["tag.ready"], "description": "", "enabled": True}


def test_update_refuses_nothing_and_contradictions(run: Run) -> None:
    _use(run)
    webhook_id = _create(run, "-e", "*")
    _, err = run("webhook", "update", webhook_id, expect=2)
    assert "--enable, or --disable" in words(err)
    _, err = run("webhook", "update", webhook_id, "--ref", "x", "--all-refs", expect=2)
    assert "not both" in err
    _, err = run("webhook", "update", webhook_id, "--header", "A: b", "--clear-headers", expect=2)
    assert "not both" in err


def test_refusals_print_the_servers_code(run: Run, bff: FakeBff) -> None:
    _use(run)
    _, err = run("webhook", "create", "--url", "https://10.0.3.7/", "-e", "*", expect=1)
    assert "WEBHOOK_URL_REFUSED" in err and "10.0.3.7" in err
    _, err = run(
        "webhook", "create", "--url", "https://x.example.com/", "-e", "entry.saved", expect=1
    )
    assert "WEBHOOK_EVENT_UNKNOWN" in err
    bff.webhooks_configured = False
    _, err = run("webhook", "create", "--url", "https://x.example.com/", "-e", "*", expect=1)
    assert "WEBHOOKS_UNCONFIGURED" in err


def test_delete_asks_first(run: Run, bff: FakeBff, monkeypatch: pytest.MonkeyPatch) -> None:
    _use(run)
    webhook_id = _create(run, "-e", "*")
    monkeypatch.setattr("sys.stdin", io.StringIO("n\n"))
    _, err = run("webhook", "delete", webhook_id, expect=1)
    assert "Aborted" in err
    assert webhook_id in bff.webhooks
    out, _ = run("--yes", "webhook", "delete", webhook_id)
    assert f"Deleted {webhook_id}." in out and webhook_id not in bff.webhooks
    _, err = run("webhook", "show", webhook_id, expect=5)
    assert "NOT_FOUND" in err


def test_rotate_prints_the_new_secret_and_when_the_old_one_stops(run: Run, bff: FakeBff) -> None:
    _use(run)
    webhook_id = _create(run, "-e", "*")
    old = bff.webhook_secrets[webhook_id]
    out, err = run("webhook", "rotate", webhook_id)
    new = bff.webhook_secrets[webhook_id]
    assert new != old and f"\n{new}\n" in out and old not in out
    assert "previous secret  signs until 2026-11-03T14:00:00Z" in out
    assert "shown once" in err


def test_test_queues_a_ping_and_delivery_shows_its_attempt(run: Run, bff: FakeBff) -> None:
    _use(run)
    webhook_id = _create(run, "-e", "*")
    out, _ = run("-o", "json", "webhook", "test", webhook_id)
    delivery_id = json.loads(out)["delivery"]
    out, _ = run("webhook", "delivery", webhook_id, delivery_id)
    assert "ping" in out and "succeeded" in out and "200" in out and "140 ms" in out


def test_delivery_shows_an_attempt_that_got_no_answer(run: Run, bff: FakeBff) -> None:
    _use(run)
    webhook_id = _create(run, "-e", "*")
    delivery_id = bff.add_delivery(
        webhook_id, status=None, error_kind="timeout", error="No answer within 15 seconds"
    )
    out, _ = run("webhook", "delivery", webhook_id, delivery_id)
    assert "timeout" in out and "No answer within 15 seconds" in words(out)
    out, _ = run("-o", "json", "webhook", "delivery", webhook_id, delivery_id)
    assert json.loads(out)["attempts"][0]["errorKind"] == "timeout"


def test_deliveries_filter(run: Run, bff: FakeBff) -> None:
    _use(run)
    webhook_id = _create(run, "-e", "*")
    bff.add_delivery(webhook_id, type="tag.ready", state="succeeded", status=200)
    late = bff.add_delivery(webhook_id, state="failed", status=503)
    out, _ = run(
        "webhook",
        "deliveries",
        webhook_id,
        "--state",
        "failed",
        "--type",
        "entries.changed",
        "--since",
        "2026-11-02T12:02",
        "--limit",
        "5",
    )
    assert late in out and "503" in out and "tag.ready" not in out
    assert bff.last().args.to_dict() == {
        "state": "failed",
        "type": "entries.changed",
        "since": "2026-11-02T12:02:00Z",
        "limit": "5",
    }
    run("webhook", "deliveries", webhook_id, "--since", "2026-11-02")
    assert bff.last().args["since"] == "2026-11-02T00:00:00Z"
    _, err = run("webhook", "deliveries", webhook_id, "--state", "lost", expect=2)
    assert "held, pending, running, succeeded, or failed" in err
    _, err = run("webhook", "deliveries", webhook_id, "--since", "yesterday", expect=2)
    assert "ISO 8601" in err


def test_redeliver_one_or_every_failure_since(run: Run, bff: FakeBff) -> None:
    _use(run)
    webhook_id = _create(run, "-e", "*")
    first = bff.add_delivery(webhook_id, created_at="2026-11-01T09:00:00Z")
    bff.add_delivery(webhook_id, created_at="2026-11-02T09:00:00Z")
    bff.add_delivery(webhook_id, created_at="2026-11-02T10:00:00Z")
    out, _ = run("webhook", "redeliver", webhook_id, first)
    assert f"Queued delivery {first} to be sent again" in out
    _, err = run("webhook", "redeliver", webhook_id, first, expect=1)
    assert "still being sent" in err
    out, _ = run("webhook", "redeliver", webhook_id, "--failed-since", "2026-11-02")
    assert "Queued 2 failed deliveries since 2026-11-02T00:00:00Z" in out
    out, _ = run("-o", "json", "webhook", "redeliver", webhook_id, "--failed-since", "2026-11-02")
    assert json.loads(out) == {"redelivered": 0}
    _, err = run("webhook", "redeliver", webhook_id, expect=2)
    assert "DELIVERY_ID" in err


def test_a_github_webhook_has_no_secret_and_shows_its_repository(
    run: Run, bff: FakeBff, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use(run)
    monkeypatch.setattr("sys.stdin", io.StringIO("ghp_from_stdin\n"))
    out, err = run(
        "webhook", "create", "--github", "acme/site", "--token", "-", "-e", "environment.promoted"
    )
    [webhook_id] = bff.webhooks
    assert bff.last().get_json() == {
        "events": ["environment.promoted"],
        "enabled": True,
        "kind": "github_dispatch",
        "repository": "acme/site",
        "token": "ghp_from_stdin",
    }
    assert "acme/site" in out and "repository_dispatch" in words(out)
    assert "Signing secret" not in out and "shown once" not in err
    assert "ghp_from_stdin" not in out
    shown, _ = run("webhook", "show", webhook_id)
    assert "github" in shown and "acme/site" in shown and "api.github.com" not in shown

    run("webhook", "update", webhook_id, "--token", "ghp_new")
    assert bff.last().get_json() == {"token": "ghp_new"}
    assert bff.webhook_headers[webhook_id] == {"Authorization": "Bearer ghp_new"}
    _, err = run("webhook", "rotate", webhook_id, expect=1)
    assert "WEBHOOK_INVALID" in err and "no secret to rotate" in words(err)


def test_a_github_webhook_in_json_is_the_whole_response(run: Run) -> None:
    _use(run)
    out, _ = run(
        "-o", "json", "webhook", "create", "--github", "acme/site", "--token", "t", "-e", "*"
    )
    body = json.loads(out)
    assert "secret" not in body and body["webhook"]["kind"] == "github_dispatch"


def test_create_refuses_a_mixed_or_missing_target(run: Run) -> None:
    _use(run)
    _, err = run("webhook", "create", "-e", "*", expect=2)
    assert "--github OWNER/NAME" in words(err)
    _, err = run("webhook", "create", "--github", "a/b", "-e", "*", expect=2)
    assert "needs --token" in words(err)
    _, err = run(
        "webhook",
        "create",
        "--github",
        "a/b",
        "--token",
        "t",
        "--url",
        "https://x.example.com/",
        "-e",
        "*",
        expect=2,
    )
    assert "leave out --url" in words(err)
    _, err = run(
        "webhook", "create", "--url", "https://x.example.com/", "--token", "t", "-e", "*", expect=2
    )
    assert "for a GitHub webhook" in words(err)
