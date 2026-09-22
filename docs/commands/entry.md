# entry

Entries on the current ref. See [content model](../content-model.md) for fields,
locales and ETags.

## `coho entry list [-t TYPE] [--limit N] [--offset N] [--all]`

One page (default 100, max 1000 — out of range is refused, not clamped), or every
page with `--all`. No collection total is reported by design; `hasMore` is what a paging
client needs, and the CLI prints the next `--offset`.

```
ID        TYPE      SLUG         TITLE
0192d6…   blogPost  hello-world  Hello, world
more: --offset 100, or --all
```

## `coho entry get ID [--fields]`

The entry and its ETag. `--fields` prints only the fields object — for editing and
feeding back to `put --file`.

## `coho entry create -t TYPE -s SLUG [-f FIELDS] [--set PATH=VALUE …]`

`POST …/entries`. Fields come from `--file` (path, `-`, or inline JSON — either the
fields object or a document with a `fields` key) and/or `--set`.

`--set path=value` sets a dotted path; the value is parsed as JSON when it parses and
taken as a string otherwise:

```
--set title.en-US="Hello"      # string
--set rank=3                   # number
--set featured=true            # boolean
--set tags='["a","b"]'         # array
--set author=0192…             # reference (a node id)
```

Refusals: `VALIDATION_FAILED` (each `errors[]` item printed as `path: message`),
`SLUG_CONFLICT`, `BRANCH_NOT_WRITABLE` (a tag or environment), `FORBIDDEN`.

## `coho entry put ID [-f FIELDS] [--set …] [--if-match ETAG] [--force]`

Two modes:

- **`--set` only:** read-modify-write. Reads the entry, applies the sets, writes back
  with the ETag it read. `VERSION_CONFLICT` (exit 4) if somebody wrote in between.
- **`--file`:** replaces the fields wholesale. Needs `--if-match` from your last read,
  or `--force` (reads the current ETag and overwrites). Without either, the CLI stops
  with `PRECONDITION_REQUIRED` before sending anything.

The slug carries forward; an update sends content, not identity.

## `coho entry delete ID [--if-match ETAG] [--force]`

Tombstones the entry — never a physical delete; the tombstone is a version with its own
ETag, which is printed. Shows how many entries still link to it and asks (`-y` skips).
Without `--if-match`, deletes the version it reads now.

## `coho entry history ID [--limit N] [--offset N]`

Versions on this ref, by `seq` descending — commit order, not wall-clock. Tombstones
included; a deleted entry still has a history. Per-ref: a feature branch shows the
trunk's history up to the branch point, then its own.

## `coho entry references ID`

What links to this entry on this ref: linking node, kind, slug, field. Complete, never
paginated — "can I delete this" needs the whole answer. Reports; never refuses.
