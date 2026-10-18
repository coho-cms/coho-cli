"""Usage reports for ``coho account usage`` and ``coho project usage`` (coho-data doc 41).

The numbers are the SDK's (`UsageReport.total` and friends), which do the portal's
arithmetic, so a terminal and the Usage pages agree. ``--output json`` prints the
report exactly as the server sent it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import typer
from coho_management_sdk.models import AccountUsageReport, UsageReport

from ._output import console, emit_json, record, table
from ._state import State, Usage

Grain = Annotated[
    str,
    typer.Option(
        "--grain", "-g", help="`hour`: the last day, hour by hour. `day`: the last 30 days."
    ),
]
Start = Annotated[
    str | None,
    typer.Option(
        "--from", help="Inclusive, ISO 8601 (2026-10-01 or 2026-10-01T09:00:00Z); rounded down."
    ),
]
End = Annotated[
    str | None, typer.Option("--to", help="Exclusive, ISO 8601; rounded up. Default: now.")
]
Meters = Annotated[
    list[str] | None,
    typer.Option("--meter", "-m", help="Only this meter, as delivery.requests; repeat for more."),
]
Periods = Annotated[
    bool, typer.Option("--periods", help="Also a line per hour or day, not just the totals.")
]

# Management requests by class, in the order the portal shows them (doc 41 §2.2).
_CLASSES = ("read", "write", "merge", "release", "export", "asset", "admin")


@dataclass(frozen=True)
class Query:
    grain: str
    start: str | None
    end: str | None
    meters: list[str] | None

    def kwargs(self) -> dict[str, Any]:
        return {"grain": self.grain, "start": self.start, "end": self.end, "meters": self.meters}


def query(grain: str, start: str | None, end: str | None, meters: list[str] | None) -> Query:
    if grain not in ("hour", "day"):
        raise Usage("--grain must be `hour` or `day`")
    return Query(grain, _instant(start), _instant(end), meters or None)


def _instant(value: str | None) -> str | None:
    """A bare date is midnight UTC: what someone typing ``--from 2026-10-01`` means."""
    if value and len(value) == 10 and value[4] == "-" and value[7] == "-":
        return f"{value}T00:00:00Z"
    return value


# -- the project's ------------------------------------------------------------


def show_project(state: State, name: str, report: UsageReport, q: Query, periods: bool) -> None:
    if state.output == "json":
        emit_json(report.raw)
        return
    _heading(f"{name}: usage", report)
    if q.meters:
        _meters(state, report)
    else:
        _project_sections(state, report)
    if periods:
        _periods(state, report)


def _project_sections(state: State, r: UsageReport) -> None:
    def outcome(o: str) -> Any:
        return lambda d: d.get("outcome") == o

    def actor(a: str) -> Any:
        return lambda d: d.get("actor") == a

    _section("Delivery")
    record(
        state,
        None,
        [
            ("requests", count(r.total("delivery.requests"))),
            ("revalidated (304)", count(r.total("delivery.requests", outcome("not_modified")))),
            ("refused", count(r.total("delivery.requests", outcome("refused")))),
            ("sent", size(r.total("delivery.bytes"))),
            (
                "billable",
                f"{size(r.total('delivery.billable_bytes'))}  (at least 16 KB a full read)",
            ),
            ("peak", f"{count(r.total('delivery.peak_rpm'))}/min"),
        ],
    )
    keys = r.delivery_by_key()
    console.print()
    table(
        state,
        None,
        ["KEY", "ACCESS", "REQUESTS", "304", "REFUSED", "SENT", f"REQUESTS/URL/{r.grain.upper()}"],
        [
            (
                "no key" if k.key == "none" else k.key,
                "keyless" if k.access == "public" else k.access,
                count(k.requests),
                count(k.not_modified),
                count(k.refused),
                size(k.bytes),
                None if k.ratio is None else f"{k.ratio:.1f}",
            )
            for k in keys
        ],
        empty="(no delivery requests in this range)",
    )
    if any(k.ratio is not None and k.ratio >= 10 for k in keys):
        console.print(
            "[dim]A client that caches asks for each URL about once per tag, and once per "
            "max-age for an environment. Tens or more per URL is one fetching the same answer "
            "again: send If-None-Match and a repeat is a 304.[/dim]"
        )

    _section("Management")
    record(
        state,
        None,
        [
            ("requests by people", count(r.total("management.requests", actor("person")))),
            ("requests by tokens", count(r.total("management.requests", actor("token")))),
            ("versions written", count(r.total("authoring.versions"))),
            ("unchanged rewrites", count(r.total("authoring.noop_versions"))),
            ("preview reads", count(r.total("preview.requests"))),
        ],
    )
    console.print()
    rows = []
    for kind, label in (("person", "people"), ("token", "project tokens")):
        by = r.totals_by("management.requests", "class", actor(kind))
        rows.append((label, *(count(by.get(c, 0)) for c in _CLASSES)))
    table(state, None, ["WHO", *(c.upper() for c in _CLASSES)], rows)

    _section("Content and history")
    record(
        state,
        None,
        [
            ("entries on trunk", count(r.total("content.records"))),
            (
                "published",
                f"{size(r.total('content.published_bytes'))}  "
                f"({_of(r.total('content.published_entries'), 'entry', 'entries')})",
            ),
            ("index on disk", size(r.total("content.index_bytes"))),
            (
                "history",
                f"{size(r.total('history.bytes'))}  "
                f"({_of(r.total('history.versions'), 'version', 'versions')})",
            ),
            ("active tokens", count(r.total("tokens.active"))),
        ],
    )

    _section("Assets")
    record(
        state,
        None,
        [
            (
                "stored",
                f"{size(r.total('assets.stored_bytes'))}  "
                f"({_of(r.total('assets.stored_count'), 'file', 'files')})",
            ),
            ("requests", count(r.total("assets.requests"))),
            ("served", size(r.total("assets.egress_bytes"))),
            (
                "transforms",
                count(
                    r.total(
                        "assets.requests",
                        lambda d: d.get("kind") == "image" and d.get("cache") == "miss",
                    )
                ),
            ),
        ],
    )
    console.print("[dim]Asset traffic comes from the CDN's logs, minutes after the request.[/dim]")


# -- the account's ------------------------------------------------------------


def show_account(
    state: State, name: str, report: AccountUsageReport, q: Query, periods: bool
) -> None:
    if state.output == "json":
        emit_json(report.raw)
        return
    _heading(f"{name}: usage across projects", report)
    if q.meters:
        _meters(state, report)
    else:
        r = report
        record(
            state,
            None,
            [
                ("delivery requests", count(r.total("delivery.requests"))),
                ("delivery billable", size(r.total("delivery.billable_bytes"))),
                ("management requests", count(r.total("management.requests"))),
                ("published content", size(r.total("content.published_bytes"))),
                ("history", size(r.total("history.bytes"))),
                ("assets stored", size(r.total("assets.stored_bytes"))),
                ("assets served", size(r.total("assets.egress_bytes"))),
            ],
        )
        _section("By project")
        table(
            state,
            None,
            [
                "PROJECT",
                "DELIVERY",
                "BILLABLE",
                "MANAGEMENT",
                "PUBLISHED",
                "HISTORY",
                "ASSETS",
            ],
            [
                (
                    p.name,
                    count(p.totals.get("delivery.requests", 0)),
                    size(p.totals.get("delivery.billable_bytes", 0)),
                    count(p.totals.get("management.requests", 0)),
                    size(p.totals.get("content.published_bytes", 0)),
                    size(p.totals.get("history.bytes", 0)),
                    size(p.totals.get("assets.stored_bytes", 0)),
                )
                for p in report.projects
            ],
            empty="(no projects)",
        )
        console.print("[dim]Each project's own detail: coho project usage <project>.[/dim]")
    if periods:
        _periods(state, report)


# -- shared -------------------------------------------------------------------


def _meters(state: State, r: UsageReport) -> None:
    """With --meter: each asked-for meter's total, then each of its series."""
    rows: list[Sequence[Any]] = []
    for m in r.meters:
        rows.append((m.meter, m.kind, _amount(r.total(m.meter), m.unit), None))
        if len(m.series) > 1 or (m.series and m.series[0].dims):
            for s in m.series:
                dims = ", ".join(f"{k}={v}" for k, v in sorted(s.dims.items()))
                rows.append(("", "", _amount(s.total, m.unit), dims))
    table(state, None, ["METER", "KIND", "TOTAL", "SERIES"], rows, empty="(no such meters)")


def _periods(state: State, r: UsageReport) -> None:
    _section(f"By {r.grain} (UTC)")
    answered = {"ok", "not_modified"}
    delivery = r.per_bucket("delivery.requests", lambda d: d.get("outcome") in answered)
    revalidated = r.per_bucket("delivery.requests", lambda d: d.get("outcome") == "not_modified")
    management = r.per_bucket("management.requests")
    served = r.per_bucket("assets.egress_bytes")
    table(
        state,
        None,
        ["PERIOD", "ANSWERED", "304", "MANAGEMENT", "ASSETS SERVED"],
        [
            (_when(b, r.grain), count(d), count(n), count(m), size(a))
            for b, d, n, m, a in zip(
                r.buckets, delivery, revalidated, management, served, strict=False
            )
        ],
    )


def _heading(text: str, r: UsageReport) -> None:
    console.print(f"[bold]{text}[/bold]", highlight=False)
    console.print(_range(r), highlight=False)
    end = _parse(r.end)
    if end is not None and end > datetime.now(UTC):
        console.print(f"[dim]The current {r.grain} is still filling.[/dim]")


def _section(title: str) -> None:
    console.print(f"\n[bold]{title}[/bold]", highlight=False)


def _range(r: UsageReport) -> str:
    """``2026-10-18 10:00 to 13:00 UTC``, or ``2026-10-16 through 2026-10-18 UTC`` by the day.

    The server's ``to`` is exclusive: a clock range reads right that way, a run of days
    does not, so a daily range names its last day.
    """
    start = _when(r.start, r.grain)
    if r.grain == "day":
        last = _when(_minus_a_day(r.end), "day")
        span = start if last == start else f"{start} through {last}"
        return f"{span} UTC, by the day"
    end = _when(r.end, r.grain)
    if start[:10] == end[:10]:
        end = end[11:]
    return f"{start} to {end} UTC, by the hour"


def _minus_a_day(at: str) -> str:
    moment = _parse(at)
    return at if moment is None else (moment - timedelta(days=1)).isoformat()


def _parse(at: str) -> datetime | None:
    try:
        return datetime.fromisoformat(at.replace("Z", "+00:00"))
    except ValueError:
        return None


def _when(at: str, grain: str) -> str:
    stamp = at.replace("T", " ").removesuffix("Z")
    return stamp[:10] if grain == "day" else stamp[:16]


def _amount(n: int, unit: str) -> str:
    return size(n) if unit == "bytes" else f"{count(n)} {unit}"


def _of(n: int, one: str, many: str) -> str:
    return f"{count(n)} {one if n == 1 else many}"


def count(n: int) -> str:
    return f"{n:,}"


def size(n: int) -> str:
    """Binary units, as the bill is written in and the portal shows."""
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.0f} {unit}" if unit == "B" else f"{_short(value)} {unit}"
        value /= 1024
    return f"{_short(value)} TB"


def _short(value: float) -> str:
    return f"{value:.0f}" if value >= 100 else f"{value:.1f}".removesuffix(".0")
