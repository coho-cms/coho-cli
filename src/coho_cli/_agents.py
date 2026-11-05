"""`coho init --agents`: describe the live project for a coding agent, in COHO.md.

A hand-written CLAUDE.md about a content model drifts the day someone adds a field. This
writes one from the project itself (its types and their fields, the locales in use, its
refs and environments, the ids that make the context reproducible) and the rules for
changing content safely. It is regenerated on demand, so it never drifts, the way
`coho-codegen pull` regenerates the types a compiler reads.

AGENTS.md (or CLAUDE.md) gets a short marked block pointing at COHO.md, merged in the way
`next dev` merges its own: the block is replaced where it is, appended where it is not,
and nothing outside the markers is touched.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from coho_management_sdk import models as m
from coho_management_sdk.client import Coho, Project

COHO_MD = "COHO.md"
AGENTS_MD = "AGENTS.md"
CLAUDE_MD = "CLAUDE.md"

START = "<!-- BEGIN:coho-agent-rules -->"
END = "<!-- END:coho-agent-rules -->"

# The first line of COHO.md, read back on the next run so the file regenerates for the
# same project wherever it is run: the ids, and the ref only when one was asked for.
_SOURCE = re.compile(r"^<!-- coho-agents: (\{.*\}) -->$", re.MULTILINE)

# Locales are whatever authors have used (there is no registry), so they are read from
# entries. A sample is enough to name them; reading every entry of a large project is not.
LOCALE_SAMPLE = 500

# Enough tags to show the naming and the latest release, not the whole history.
TAGS_SHOWN = 10


@dataclass
class Source:
    """Which project COHO.md describes, as recorded in it."""

    url: str | None
    account: str
    project: str
    ref: str | None = None

    def header(self) -> str:
        body = {"url": self.url, "account": self.account, "project": self.project}
        if self.ref:
            body["ref"] = self.ref
        return f"<!-- coho-agents: {json.dumps(body, separators=(', ', ': '))} -->"


def read(path: Path) -> str | None:
    """A file's text exactly as stored, line endings included, or None when it is missing.

    ⚠️ Never `read_text()`: it turns CRLF into LF, so writing back would rewrite every line
    of somebody else's AGENTS.md.
    """
    try:
        with path.open(encoding="utf-8", newline="") as f:
            return f.read()
    except FileNotFoundError:
        return None


def recorded_source(directory: Path) -> Source | None:
    """The project an existing COHO.md was generated from, or None."""
    text = read(directory / COHO_MD)
    if text is None:
        return None
    found = _SOURCE.search(text)
    if not found:
        return None
    try:
        raw = json.loads(found.group(1))
        return Source(raw.get("url"), str(raw["account"]), str(raw["project"]), raw.get("ref"))
    except (ValueError, KeyError, TypeError):
        return None


def codegen_source(directory: Path) -> Source | None:
    """The project `coho.config.json` names, for `@coho-cms/codegen`, beside this one."""
    try:
        raw = json.loads((directory / "coho.config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict) or not raw.get("account") or not raw.get("project"):
        return None
    return Source(raw.get("url"), str(raw["account"]), str(raw["project"]))


# --------------------------------------------------------------------------------------
# What the project says about itself
# --------------------------------------------------------------------------------------


@dataclass
class Credential:
    """The project token COHO.md was generated with, if it was one. A person is never named."""

    label: str | None
    role: str


@dataclass
class Snapshot:
    source: Source
    account_name: str | None
    project_name: str
    trunk: str
    ref: str
    refs: list[m.RefInfo]
    environments: list[m.Environment]
    types: list[m.ContentType]
    traits: list[m.Trait]
    locales: list[tuple[str, int]]
    sampled: int
    total_entries: int | None
    # Entries per type in the sample: which type the examples use, never printed, since a
    # count would change the file on every new entry.
    in_use: dict[str, int] = field(default_factory=dict)
    token: Credential | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def gather(coho: Coho, source: Source, *, account_name: str | None) -> Snapshot:
    """Read everything COHO.md says from the server. Reads only."""
    project: Project = coho.account(source.account).project(source.project)
    info = project.info()
    ref_name = source.ref or info.trunk
    ref = project.ref(ref_name)
    types = ref.types.list(effective=True)
    traits = ref.traits.list()
    locales, sampled, total, in_use = _locales(ref, types)
    token = None
    if coho.uses_project_token:
        d = coho.describe_token()
        token = Credential(d.label, d.role)
        account_name = account_name or d.account_name
    return Snapshot(
        source=source,
        account_name=account_name,
        project_name=info.name,
        trunk=info.trunk,
        ref=ref_name,
        refs=project.refs.list(),
        environments=project.environments.list(),
        types=types,
        traits=traits,
        locales=locales,
        sampled=sampled,
        total_entries=total,
        in_use=in_use,
        token=token,
    )


def _locales(
    ref: Any, types: list[m.ContentType]
) -> tuple[list[tuple[str, int]], int, int | None, dict[str, int]]:
    """The locales entries use, most used first, from the first `LOCALE_SAMPLE` entries; and
    how many of those entries each type has."""
    localized = {
        t.slug: {f["id"] for f in t.definition.get("fields", []) if f.get("localized")}
        for t in types
    }
    seen: Counter[str] = Counter()
    per_type: Counter[str] = Counter()
    page = ref.entries.list(limit=LOCALE_SAMPLE)
    for entry in page.entries:
        per_type[entry.type] += 1
        for fid in localized.get(entry.type, ()):
            value = entry.fields.get(fid)
            if isinstance(value, dict):
                seen.update(k for k in value if value[k] not in (None, "", []))
    total = page.raw.get("total") if isinstance(page.raw, dict) else None
    locales = sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))
    return locales, len(page.entries), total, dict(per_type)


# --------------------------------------------------------------------------------------
# COHO.md
# --------------------------------------------------------------------------------------


def render(s: Snapshot, *, regenerate: str) -> str:
    """COHO.md for [s]. Deterministic: the same project renders the same file."""
    out: list[str] = [s.source.header(), ""]
    add = out.append
    project_label = f"{s.project_name}"
    add(f"# {project_label}: content in Coho")
    add("")
    add(
        "This project's content lives in [Coho](https://github.com/coho-cms/coho-cli), and is "
        "read and changed with the `coho` CLI. This file describes it as the server does: its "
        "content types and fields, the locales in use, and its refs and environments, with the "
        "rules for changing content."
    )
    add("")
    add(
        f"> Generated by `{regenerate}` from the live project. Do not edit it: regenerate it "
        "after the content model changes, and commit it. A regenerated file that differs is "
        "the model having changed, not noise."
    )
    add("")

    _context(s, add)
    _rules(s, add)
    _refs(s, add)
    _locales_section(s, add)
    _types(s, add)
    _commands(s, add)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


def _context(s: Snapshot, add: Any) -> None:
    acct = f"{s.account_name} (`{s.source.account}`)" if s.account_name else f"`{s.source.account}`"
    add("## Context")
    add("")
    add("| | |")
    add("|---|---|")
    if s.source.url:
        add(f"| Server | `{s.source.url}` |")
    add(f"| Account | {acct} |")
    add(f"| Project | {s.project_name} (`{s.source.project}`) |")
    add(f"| Trunk | `{s.trunk}` |")
    add(f"| Types read from | `{s.ref}` |")
    add("")
    add(
        "Pass the ids rather than relying on whatever context the machine has saved, so every "
        "command reaches this project:"
    )
    add("")
    add("```bash")
    ids = f"--account {s.source.account} --project {s.source.project}"
    add(f"coho -o json {ids} --ref {s.trunk} status")
    add("```")
    add("")
    add(
        "Or once, for a shell: `export COHO_ACCOUNT="
        f"{s.source.account} COHO_PROJECT={s.source.project}`."
    )
    add("")
    add(
        "**Run `coho -o json status` first.** It says which credential is in use, its role in "
        'this project, and the permissions that role holds (`permissions`; `["*"]` is '
        "everything). Do only what those permissions allow."
    )
    if s.token:
        label = f' "{s.token.label}"' if s.token.label else ""
        perms = ", ".join(f"`{p}`" for p in m.permissions_for(s.token.role)) or "none"
        add("")
        add(
            f"This file was generated with the project token{label}, role `{s.token.role}`: "
            f"{perms}. If that is your credential too, that is what you may do."
        )
    add("")


def _rules(s: Snapshot, add: Any) -> None:
    add("## Rules")
    add("")
    rules = [
        "**Use `-o json`** (a global option: `coho -o json entry list`) and parse the output. "
        "Errors arrive on stderr as `error CODE: detail`; act on the code.",
        "**Read before you write.** `coho -o json entry get ID` shows the entry and its ETag. "
        "Change it from what you read.",
        "**Every replacing write carries the ETag.** `coho entry put ID --set field=value` reads "
        "and sends `If-Match` itself; `coho entry put ID --file f.json --if-match '\"ETAG\"'` "
        "and `coho type put SLUG --file def.json --if-match '\"ETAG\"'` need it given. Never "
        "use `--force`.",
        "**Exit code 4 means re-read.** Someone else changed it first (`VERSION_CONFLICT`, "
        "`MERGE_REFS_MOVED`, `ENVIRONMENT_MOVED`): get it again, reapply your change, then "
        "write. Do not retry the same write.",
        f"**Write on a branch, never on `{s.trunk}` directly.** Ask which branch, or create one "
        "with `coho branch create NAME`. Tags and environments are read-only.",
        "**Never merge, tag, promote or roll back.** `coho merge`, `coho tag create`, "
        "`coho promote` and `coho rollback` decide what is released: tell the person the "
        "command, and let them run it.",
        "**Ask before anything destructive**: a delete, `--confirm-destructive`, `--yes`. A "
        'field is removed in two steps, `"omitted": true` first.',
        "**Exit code 3 means nobody is signed in.** A person runs `coho login` in their own "
        "terminal; never ask them for a code, password or token.",
    ]
    for rule in rules:
        add(f"- {rule}")
    add("")


def _refs(s: Snapshot, add: Any) -> None:
    add("## Refs and environments")
    add("")
    branches = [r for r in s.refs if r.kind in ("version_branch", "branch")]
    tags = [r for r in s.refs if r.kind == "tag"]
    add(
        "A ref is a branch, a tag or an environment. Branches are written; a tag is an "
        "immutable release; an environment is a name a website reads, pointed at a tag "
        "(or, for a live tier, a branch) by a promotion."
    )
    add("")
    if branches:
        add("**Branches**")
        add("")
        for r in branches:
            kind = "trunk" if r.name == s.trunk else r.kind.replace("_", " ")
            add(f"- `{r.name}`: {kind}")
        add("")
    if s.environments:
        add("**Environments**, in promotion order")
        add("")
        add("| Environment | Tier | Reads | Points at |")
        add("|---|---|---|---|")
        for e in s.environments:
            target = f"`{e.target}`" if e.target else "unset"
            add(f"| `{e.name}` | {e.tier} | {e.resolves} | {target} |")
        add("")
    if tags:
        shown = sorted(tags, key=lambda r: r.raw.get("at") or 0)[-TAGS_SHOWN:]
        more = f" (the latest {len(shown)} of {len(tags)})" if len(tags) > len(shown) else ""
        add(f"**Tags**{more}")
        add("")
        for r in reversed(shown):
            note = f": {r.description}" if r.description else ""
            add(f"- `{r.name}`{note}")
        add("")


def _locales_section(s: Snapshot, add: Any) -> None:
    add("## Locales")
    add("")
    if not s.locales:
        add(
            "No entry holds a localized value yet. A localized field's value is an object "
            'keyed by locale, such as `{"en-US": "Hello"}`.'
        )
        add("")
        return
    names = ", ".join(f"`{loc}`" for loc, _ in s.locales)
    if s.total_entries and s.total_entries > s.sampled:
        read = f"the first {s.sampled} of {s.total_entries} entries"
    else:
        read = f"all {s.sampled} entries"
    add(
        f"In use: {names}, read from {read}. Coho keeps no list of locales: these are the ones "
        "authors have written."
    )
    add("")
    first = s.locales[0][0]
    add(
        f"A localized field's value is an object keyed by locale. Set one locale with a dotted "
        f'path, `--set title.{first}="…"`; the others are left as they are. Use these locales, '
        "not new ones, unless asked."
    )
    add("")


def _field_line(f: dict[str, Any], help_text: str | None) -> str:
    attrs: list[str] = [f["type"] + (" list" if f.get("many") else "")]
    if f.get("required"):
        attrs.append("required")
    if f.get("localized"):
        attrs.append("localized")
    if f.get("of"):
        attrs.append("of " + ", ".join(f"`{t}`" for t in f["of"]))
    if f.get("values"):
        attrs.append("one of " + ", ".join(f"`{v}`" for v in f["values"]))
    if f.get("textFormat") and f["textFormat"] != "plain":
        attrs.append(str(f["textFormat"]))
    if f.get("min") is not None:
        attrs.append(f"min {f['min']}")
    if f.get("max") is not None:
        attrs.append(f"max {f['max']}")
    if f.get("omitted"):
        attrs.append("omitted: being removed, do not write")
    origin = f.get("from") or {}
    if origin.get("trait"):
        attrs.append(f"from trait `{origin['trait']}`")
    elif origin.get("type") and origin.get("type") != f.get("_owner"):
        attrs.append(f"from `{origin['type']}`")
    name = f" ({f['name']})" if f.get("name") and f["name"] != f["id"] else ""
    tail = f". {help_text}" if help_text else ""
    return f"- `{f['id']}`{name}: {', '.join(attrs)}{tail}"


def _type_block(t: m.ContentType, add: Any) -> None:
    d = t.definition
    marks: list[str] = []
    if d.get("abstract"):
        marks.append("abstract: no entries of its own; the types that extend it have them")
    if d.get("singleton"):
        marks.append("singleton: one entry per ref")
    if d.get("extends"):
        marks.append(f"extends `{d['extends']}`")
    if d.get("traits"):
        marks.append("traits " + ", ".join(f"`{x}`" for x in d["traits"]))
    name = d.get("_name") or t.slug
    add(f"### `{t.slug}`: {name}")
    add("")
    if marks:
        sentence = "; ".join(marks)
        add(sentence[0].upper() + sentence[1:] + ".")
        add("")
    controls = (d.get("editor") or {}).get("controls") or {}
    for f in d.get("fields", []):
        help_text = (controls.get(f["id"]) or {}).get("help")
        add(_field_line({**f, "_owner": t.slug}, help_text))
    add("")


def _types(s: Snapshot, add: Any) -> None:
    content = sorted((t for t in s.types if t.raw.get("kind") != "component"), key=lambda t: t.slug)
    components = sorted(
        (t for t in s.types if t.raw.get("kind") == "component"), key=lambda t: t.slug
    )
    add(f"## Content types on `{s.ref}`")
    add("")
    add(
        "Every field each type has, inherited and from traits included. A type slug is "
        "camelCase; an entry slug is kebab-case. A reference holds entry ids; with `list`, "
        "an array of them."
    )
    add("")
    if not content:
        add("None yet.")
        add("")
    for t in content:
        _type_block(t, add)
    if components:
        add("## Component types")
        add("")
        add(
            "A repeater's items. Each item is an object with its fields and `_type` naming its "
            "component; the server assigns its `_id`. A component has no entries of its own."
        )
        add("")
        for t in components:
            _type_block(t, add)
    if s.traits:
        add("## Traits")
        add("")
        add(
            "Fields a type takes by naming the trait; they appear above under each type "
            "that has it."
        )
        add("")
        for tr in sorted(s.traits, key=lambda x: x.slug):
            fields = ", ".join(f"`{f['id']}`" for f in tr.definition.get("fields", []))
            add(f"- `{tr.slug}` ({tr.definition.get('_name') or tr.slug}): {fields}")
        add("")


def _commands(s: Snapshot, add: Any) -> None:
    writable = [
        t for t in s.types if t.raw.get("kind") != "component" and not t.definition.get("abstract")
    ]
    # The type with the most entries, so the examples name one this project really uses.
    example = min(writable, key=lambda t: (-s.in_use.get(t.slug, 0), t.slug), default=None)
    loc = s.locales[0][0] if s.locales else "en-US"
    lines = [
        ("coho -o json status", "who you are here, and what you may do"),
        ("coho -o json type list", "the types, as above"),
    ]
    if example:
        # Its own fields first: a trait's, such as an SEO title, make a poor example.
        fields = sorted(
            example.definition.get("fields", []),
            key=lambda f: bool((f.get("from") or {}).get("trait")),
        )
        text = next(
            (f for f in fields if f["type"] == "text" and f.get("localized")),
            next((f for f in fields if f["type"] == "text"), None),
        )
        lines.append((f"coho -o json entry list --type {example.slug}", ""))
        lines.append(("coho -o json entry get ID", "the entry, and its ETag"))
        lines.append(("coho branch create NAME", "a branch to work on, from the current ref"))
        if text:
            path = f"{text['id']}.{loc}" if text.get("localized") else text["id"]
            put = f'coho -o json --ref NAME entry put ID --set {path}="…"'
            lines.append((put, "reads, then writes with If-Match"))
    else:
        lines.append(("coho branch create NAME", "a branch to work on, from the current ref"))
    lines.append(
        (f"coho -o json --ref NAME diff {s.trunk}", "what merging the branch would change")
    )
    width = max(len(cmd) for cmd, _ in lines)
    add("## Commands for this project")
    add("")
    add("```bash")
    for cmd, note in lines:
        add(f"{cmd.ljust(width)}  # {note}" if note else cmd)
    add("```")
    add("")
    add(
        "`coho <command> --help` lists every flag and links its page in the docs. Regenerate "
        "this file with `coho init --agents` after the content model changes."
    )


# --------------------------------------------------------------------------------------
# AGENTS.md and CLAUDE.md
# --------------------------------------------------------------------------------------


# One paragraph per line, as Markdown wants; joined so no source line runs long.
_BLOCK_BODY = (
    "# Content lives in Coho",
    " ".join(
        (
            "This project's content (its types, entries and releases) lives in Coho and is",
            "changed with the `coho` CLI. Before reading or changing content, read `COHO.md`:",
            "its content types and fields, locales, refs and environments, and the rules for",
            "writing. @COHO.md",
        )
    ),
    " ".join(
        (
            "This block and `COHO.md` are written by `coho init --agents` from the live",
            "project. Regenerate them after the content model changes rather than editing",
            "them. Removing this block from a diff only re-creates it on the next run; commit",
            "it with your work.",
        )
    ),
)


def block() -> str:
    return "\n\n".join((START, *_BLOCK_BODY, END))


def _eol(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def upsert(existing: str, managed: str) -> str:
    """[managed] in place of the block in [existing], or appended. Nothing else changes."""
    eol = _eol(existing)
    managed = managed.replace("\n", eol)
    start = existing.find(START)
    end = existing.find(END, start) if start != -1 else -1
    if start != -1 and end != -1:
        return existing[:start] + managed + existing[end + len(END) :]
    if not existing:
        return managed + eol
    # A blank line between what was there and the block, however the file ended.
    separator = eol if existing.endswith("\n") else eol * 2
    return existing + separator + managed + eol


def plan_pointers(directory: Path) -> dict[str, str]:
    """The new contents of AGENTS.md and CLAUDE.md, for those that change.

    - AGENTS.md exists: the block goes there. CLAUDE.md, if it neither imports AGENTS.md
      nor holds the block, gets the block too, since Claude Code would not see it; if
      there is no CLAUDE.md, it is created as `@AGENTS.md`.
    - Only CLAUDE.md exists: the block goes there.
    - Neither: AGENTS.md with the block, and CLAUDE.md importing it, as `next dev` does.
    """
    agents_path, claude_path = directory / AGENTS_MD, directory / CLAUDE_MD
    agents, claude = read(agents_path), read(claude_path)
    managed = block()
    changes: dict[str, str] = {}
    if agents is None and claude is not None and "@AGENTS.md" not in claude:
        updated = upsert(claude, managed)
        if updated != claude:
            changes[CLAUDE_MD] = updated
        return changes
    updated = upsert(agents or "", managed)
    if updated != agents:
        changes[AGENTS_MD] = updated
    if claude is None:
        changes[CLAUDE_MD] = "@AGENTS.md\n"
    elif "@AGENTS.md" not in claude:
        updated = upsert(claude, managed)
        if updated != claude:
            changes[CLAUDE_MD] = updated
    return changes
