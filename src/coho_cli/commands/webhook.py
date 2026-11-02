"""webhook: the endpoints Coho calls when something happens in the project, and their log.

Owners only (coho-data doc 70). Every request is signed with the webhook's own secret, which
`create` and `rotate` print once.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

import typer
from coho_management_sdk.models import Webhook, WebhookAttempt, WebhookDelivery

from .._output import console, emit_json, record, say, secret_once, short, table
from .._state import State, Usage, get_state

app = typer.Typer(
    help="Webhooks: the endpoints Coho calls when something happens in the project.",
    no_args_is_help=True,
)

STATES = ("held", "pending", "running", "succeeded", "failed")

WebhookId = Annotated[
    str, typer.Argument(metavar="ID", help="The webhook's id, as `coho webhook list` shows it.")
]
DeliveryId = Annotated[
    str,
    typer.Argument(
        metavar="DELIVERY_ID", help="The delivery's id, as `coho webhook deliveries` shows it."
    ),
]
Refs = Annotated[
    list[str] | None,
    typer.Option(
        "--ref",
        metavar="PATTERN",
        help="Only events on refs that match: a name, with * and ? as wildcards. Repeatable.",
    ),
]
Headers = Annotated[
    list[str] | None,
    typer.Option(
        "--header",
        metavar="'Name: value'",
        help="A header sent with every request, such as an Authorization a receiver checks. "
        "Repeatable, at most five. Its value is never shown again.",
    ),
]
Description = Annotated[
    str | None, typer.Option("--description", help="What it is for, up to 500 characters.")
]


def _state(ctx: typer.Context) -> State:
    state = get_state(ctx)
    state.forbidden_hint = "Only the project's owners manage its webhooks and read their log."
    return state


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """The project's webhooks: where each sends, what, and how its deliveries have gone."""
    state = _state(ctx)
    hooks = state.project().webhooks.list()
    table(
        state,
        hooks.raw,
        ["ID", "HOST", "EVENTS", "STATE", "LAST 24H"],
        [(w.id, w.host, w.events, _standing(w), _day(w)) for w in hooks.webhooks],
        empty="(no webhooks)",
        whole=["ID"],
    )
    if state.output != "json" and hooks.webhooks:
        console.print(f"\n{len(hooks.webhooks)} of {hooks.limit} webhooks.", highlight=False)


@app.command("events")
def events(ctx: typer.Context) -> None:
    """The events a webhook can subscribe to, and their groups."""
    state = _state(ctx)
    available = state.project().webhooks.events()
    table(state, available.raw, ["EVENT"], [(e,) for e in available.events])
    if state.output != "json":
        console.print(f"\nGroups: {_and(available.groups)}. `*` is every event.", highlight=False)


@app.command("create")
def create(
    ctx: typer.Context,
    url: Annotated[str, typer.Option("--url", help="Where to send: HTTPS, on a public address.")],
    events: Annotated[
        list[str],
        typer.Option(
            "--event",
            "-e",
            metavar="TYPE",
            help="An event type, a group such as tag.*, or * for every event. Repeatable; "
            "`coho webhook events` lists them.",
        ),
    ],
    refs: Refs = None,
    headers: Headers = None,
    description: Description = None,
    disabled: Annotated[
        bool,
        typer.Option(
            "--disabled",
            help="Create it turned off; `coho webhook update ID --enable` turns it on.",
        ),
    ] = False,
) -> None:
    """Add a webhook. ⚠️ Its signing secret is printed once, now, and never again."""
    state = _state(ctx)
    created = state.project().webhooks.create(
        url=url,
        events=events,
        refs=refs or None,
        headers=_headers(headers) if headers else None,
        description=description,
        enabled=not disabled,
    )
    w = created.webhook
    secret_once(
        state,
        created.raw,
        "Signing secret",
        created.secret,
        extra=[
            ("id", w.id),
            ("url", w.url or w.host),
            ("events", w.events),
            ("refs", w.refs or "(all)"),
            ("headers", w.headers),
            ("enabled", w.enabled),
        ],
    )
    say(
        state,
        "Check each request's webhook-signature header with it, as Standard Webhooks describes. "
        f"`coho webhook test {w.id}` sends a ping.",
    )


@app.command("show")
def show(ctx: typer.Context, webhook_id: WebhookId) -> None:
    """One webhook, with its full URL. Never its secret, nor its headers' values."""
    state = _state(ctx)
    _show(state, state.project().webhooks.get(webhook_id))


@app.command("update")
def update(
    ctx: typer.Context,
    webhook_id: WebhookId,
    url: Annotated[
        str | None, typer.Option("--url", help="Where to send instead: HTTPS, on a public address.")
    ] = None,
    events: Annotated[
        list[str] | None,
        typer.Option(
            "--event",
            "-e",
            metavar="TYPE",
            help="The events to send, replacing the ones it has. Repeatable.",
        ),
    ] = None,
    refs: Annotated[
        list[str] | None,
        typer.Option(
            "--ref",
            metavar="PATTERN",
            help="The ref patterns, replacing the ones it has. Repeatable.",
        ),
    ] = None,
    all_refs: Annotated[
        bool, typer.Option("--all-refs", help="Send every ref's events again.")
    ] = False,
    headers: Annotated[
        list[str] | None,
        typer.Option(
            "--header",
            metavar="'Name: value'",
            help="The custom headers, replacing every one it has, since their values cannot "
            "be read back. Repeatable.",
        ),
    ] = None,
    clear_headers: Annotated[
        bool, typer.Option("--clear-headers", help="Send no custom headers.")
    ] = False,
    description: Annotated[
        str | None, typer.Option("--description", help="What it is for; '' clears it.")
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option(
            "--enable/--disable",
            help="--enable turns it on, and clears a run of failures that turned it off; "
            "--disable turns it off.",
            show_default=False,
        ),
    ] = None,
) -> None:
    """Change a webhook. What you leave out stays as it is."""
    if refs and all_refs:
        raise Usage("pass --ref or --all-refs, not both")
    if headers and clear_headers:
        raise Usage("pass --header or --clear-headers, not both")
    nothing = (url, events, refs, headers, description, enabled)
    if all(v is None or v == [] for v in nothing) and not all_refs and not clear_headers:
        raise Usage(
            "say what to change: --url, --event, --ref, --all-refs, --header, --clear-headers, "
            "--description, --enable, or --disable"
        )
    state = _state(ctx)
    changed = state.project().webhooks.update(
        webhook_id,
        url=url,
        events=events or None,
        refs=[] if all_refs else (refs or None),
        headers={} if clear_headers else (_headers(headers) if headers else None),
        description=description,
        enabled=enabled,
    )
    _show(state, changed)


@app.command("delete")
def delete(ctx: typer.Context, webhook_id: WebhookId) -> None:
    """Delete a webhook, with its deliveries and their log."""
    state = _state(ctx)
    if not state.yes and not typer.confirm(
        f"Delete webhook {webhook_id}, with its deliveries and their log?"
    ):
        raise typer.Abort()
    state.project().webhooks.delete(webhook_id)
    say(state, f"Deleted {webhook_id}.")


@app.command("rotate")
def rotate(ctx: typer.Context, webhook_id: WebhookId) -> None:
    """A new signing secret, printed once. The previous one goes on signing beside it for a day."""
    state = _state(ctx)
    rotated = state.project().webhooks.rotate_secret(webhook_id)
    until = rotated.previous_secret_until
    secret_once(
        state,
        rotated.raw,
        "Signing secret",
        rotated.secret,
        extra=[("id", webhook_id), ("previous secret", f"signs until {until}" if until else None)],
    )
    if until:
        say(
            state,
            f"Until {until} each request carries both signatures, so give your receiver the "
            "new secret before then. Rotating again before then stops the previous one at once.",
        )


@app.command("test")
def test(ctx: typer.Context, webhook_id: WebhookId) -> None:
    """Send the webhook a ping. It is queued, and sent within seconds."""
    state = _state(ctx)
    delivery_id = state.project().webhooks.test(webhook_id)
    if state.output == "json":
        emit_json({"delivery": delivery_id})
        return
    say(
        state,
        f"Queued a ping: delivery {delivery_id}. "
        f"`coho webhook delivery {webhook_id} {delivery_id}` shows how it went.",
    )


@app.command("deliveries")
def deliveries(
    ctx: typer.Context,
    webhook_id: WebhookId,
    state_: Annotated[
        str | None,
        typer.Option(
            "--state",
            metavar="S",
            help="held, pending, running, succeeded, or failed.",
        ),
    ] = None,
    type_: Annotated[
        str | None, typer.Option("--type", metavar="T", help="One event type, as tag.ready.")
    ] = None,
    since: Annotated[
        str | None,
        typer.Option(
            "--since",
            metavar="TIME",
            help="Made at or after this: ISO 8601, as 2026-11-02T14:00:00Z, or a date. UTC "
            "unless it says otherwise.",
        ),
    ] = None,
    before: Annotated[
        str | None,
        typer.Option(
            "--before",
            metavar="TIME",
            help="Made before this, for the next page: the last CREATED shown.",
        ),
    ] = None,
    limit: Annotated[
        int | None, typer.Option("--limit", metavar="N", min=1, max=200, help="Default 50.")
    ] = None,
) -> None:
    """The webhook's log, newest first."""
    if state_ is not None and state_ not in STATES:
        raise Usage(f"--state is one of {_or(STATES)}")
    state = _state(ctx)
    log = state.project().webhooks.deliveries(
        webhook_id,
        state=state_,
        type=type_,
        since=_time(since, "--since"),
        before=_time(before, "--before"),
        limit=limit,
    )
    table(
        state,
        log.raw,
        ["DELIVERY", "CREATED", "TYPE", "STATE", "RESULT"],
        [(d.id, d.created_at, d.type, d.state, _result(d)) for d in log.deliveries],
        empty="(no deliveries)",
        whole=["DELIVERY"],
    )


@app.command("delivery")
def delivery(ctx: typer.Context, webhook_id: WebhookId, delivery_id: DeliveryId) -> None:
    """One delivery and every attempt it made: status, error, time taken, and response."""
    state = _state(ctx)
    detail = state.project().webhooks.delivery(webhook_id, delivery_id)
    if state.output == "json":
        emit_json(detail.raw)
        return
    d = detail.delivery
    record(
        state,
        None,
        [
            ("delivery", d.id),
            ("event", d.event_id),
            ("type", d.type),
            ("ref", d.ref),
            ("state", d.state),
            ("created", d.created_at),
            ("finished", d.finished_at),
            ("next attempt", d.next_attempt_at),
        ],
    )
    console.print()
    table(
        state,
        None,
        ["#", "STARTED", "STATUS", "ERROR", "TOOK", "RESPONSE"],
        [
            (a.n, a.started_at, a.response_status, a.error_kind, f"{a.duration_ms} ms", _said(a))
            for a in detail.attempts
        ],
        empty="(no attempts yet)",
    )


@app.command("redeliver")
def redeliver(
    ctx: typer.Context,
    webhook_id: WebhookId,
    delivery_id: Annotated[
        str | None,
        typer.Argument(
            metavar="[DELIVERY_ID]", help="The delivery to send again, once it has finished."
        ),
    ] = None,
    failed_since: Annotated[
        str | None,
        typer.Option(
            "--failed-since",
            metavar="TIME",
            help="Instead, every delivery that failed since this: ISO 8601 or a date, UTC "
            "unless it says otherwise.",
        ),
    ] = None,
) -> None:
    """Send a delivery again, with the same event id, or every one that failed since a time."""
    if (delivery_id is None) == (failed_since is None):
        raise Usage("name one DELIVERY_ID, or pass --failed-since TIME, but not both")
    state = _state(ctx)
    hooks = state.project().webhooks
    if delivery_id is not None:
        count = hooks.redeliver(webhook_id, delivery_id)
        message = f"Queued delivery {delivery_id} to be sent again, with the same event id."
    else:
        since = _time(failed_since, "--failed-since")
        assert since is not None
        count = hooks.redeliver_failed(webhook_id, since)
        failures = "1 failed delivery" if count == 1 else f"{count} failed deliveries"
        message = f"Queued {failures} since {since} to be sent again."
    if state.output == "json":
        emit_json({"redelivered": count})
    else:
        say(state, message)


def _show(state: State, w: Webhook) -> None:
    pairs: list[tuple[str, object]] = [
        ("id", w.id),
        ("url", w.url or w.host),
        ("description", w.description),
        ("events", w.events),
        ("refs", w.refs or "(all)"),
        ("headers", w.headers),
        ("state", _standing(w)),
    ]
    if w.previous_secret_until:
        pairs.append(("previous secret", f"signs until {w.previous_secret_until}"))
    pairs += [
        ("last delivery", _last(w)),
        ("last 24h", _day(w)),
        ("created", f"{w.created_at} by {short(w.created_by)}"),
        ("updated", w.updated_at),
    ]
    record(state, w.raw, pairs)


def _standing(w: Webhook) -> str:
    if not w.enabled:
        return f"disabled: {w.disabled_reason}" if w.disabled_reason else "disabled"
    return f"failing since {w.failing_since}" if w.failing_since else "enabled"


def _last(w: Webhook) -> str | None:
    h = w.health
    if h is None or h.last_state is None:
        return None
    return f"{h.last_state} {h.last_at}" if h.last_at else h.last_state


def _day(w: Webhook) -> str | None:
    h = w.health
    return None if h is None else f"{h.succeeded_24h} ok, {h.failed_24h} failed"


def _result(d: WebhookDelivery) -> str | None:
    """The last attempt's status, or what went wrong when there was no answer, and how many
    attempts it took when it was more than one."""
    last = str(d.last_status) if d.last_status is not None else d.last_error_kind
    if last is None or d.attempts <= 1:
        return last
    return f"{last} after {d.attempts} attempts"


def _said(a: WebhookAttempt, width: int = 60) -> str | None:
    """The response's first words on one line, or what went wrong when there was none."""
    text = a.response_body if a.response_body else a.error
    if not text:
        return None
    flat = " ".join(text.split())
    return flat if len(flat) <= width else flat[: width - 1] + "…"


def _headers(values: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for value in values:
        name, colon, rest = value.partition(":")
        name = name.strip()
        if not colon or not name:
            raise Usage(
                f"--header takes 'Name: value', such as 'Authorization: Bearer …'; got {value!r}"
            )
        if name.lower() in (h.lower() for h in headers):
            raise Usage(f"--header names {name} twice")
        headers[name] = rest.strip()
    return headers


def _time(value: str | None, flag: str) -> str | None:
    """ISO 8601 as the server takes it. A bare date is midnight UTC, and a time with no zone
    is UTC, which is what someone typing either at a terminal means."""
    if value is None:
        return None
    try:
        moment = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        raise Usage(
            f"{flag} is an ISO 8601 time, such as 2026-11-02T14:00:00Z, or a date, such as "
            "2026-11-02"
        ) from None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.isoformat().replace("+00:00", "Z")


def _and(items: list[str] | tuple[str, ...]) -> str:
    return _series(items, "and")


def _or(items: list[str] | tuple[str, ...]) -> str:
    return _series(items, "or")


def _series(items: list[str] | tuple[str, ...], word: str) -> str:
    """A list in words, with the serial comma: a, b, and c."""
    items = list(items)
    if len(items) <= 2:
        return f" {word} ".join(items)
    return f"{', '.join(items[:-1])}, {word} {items[-1]}"
