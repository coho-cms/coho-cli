# Content model

## Type definitions

A content type is a JSON definition with a display name and a list of fields:

```json
{
  "_name": "Blog post",
  "fields": [
    { "id": "title",       "type": "text",      "required": true, "localized": true },
    { "id": "body",        "type": "longText",  "localized": true },
    { "id": "publishedAt", "type": "datetime" },
    { "id": "rank",        "type": "integer",   "min": 0 },
    { "id": "featured",    "type": "boolean" },
    { "id": "meta",        "type": "json" },
    { "id": "author",      "type": "reference", "of": ["teamMember"] },
    { "id": "related",     "type": "reference", "of": ["blogPost", "caseStudy"], "many": true, "max": 3 },
    { "id": "sections",    "type": "repeater",  "of": ["hero", "quote"] }
  ]
}
```

`coho type put SLUG --file def.json` accepts either the definition itself or a wrapper
`{"definition": …, "confirmDestructive": true}`.

### Field attributes

| Key | Meaning |
|---|---|
| `id` | Immutable, camelCase, starts with a letter. `_` is reserved for system keys. Documents key on it. |
| `name` | Optional label. Renaming a label is not a migration. |
| `type` | One of the types below. |
| `required` | Validation on write. |
| `localized` | The value is an object keyed by locale (`{"en-US": …, "de-DE": …}`). |
| `omitted` | Phase one of removing a field: hidden from the API, data retained, reversible. |
| `of` | Required on `reference` (target content types) and `repeater` (component types); rejected elsewhere. |
| `many` | `reference` only: the value is an array of ids. |
| `min`, `max` | Bounds on collections and numbers. For `multichoice`, the number of values chosen. |
| `values` | Required on `choice` and `multichoice`: the permitted strings. Unique, non-empty. |
| `textFormat` | On `longText` only: `plain` (the default), `markdown` or `html`. Metadata for consumers; the value is stored as given. |

### Field types (wire names)

`text`, `longText`, `number`, `integer`, `boolean`, `datetime`, `json`, `reference`,
`repeater`, `choice`, `multichoice`.

A `choice` is one string from `values`, a closed list the type defines. A `multichoice`
is a set of them. Removing a value from the list does not discard stored entries, but
an entry still holding it is refused on its next save until it is corrected.
Use `reference` for anything that needs its own record, such as tags or authors.

`repeater` and `json` are stored but not indexed, so delivery can neither sort nor
filter on them.

### Destructive changes

Removing a field, narrowing a type or dropping a locale is refused with
`DESTRUCTIVE_SCHEMA_CHANGE` unless you pass `--confirm-destructive`. The intended
ritual is two-phase: set `"omitted": true` first (reversible), remove it in a later
change. Deleting a type that still has entries is refused with `TYPE_IN_USE`;
`coho type delete SLUG --confirm-destructive` orphans them deliberately.

### ETags on types

`coho type get SLUG` prints the type's ETag. Updating needs it (`--if-match`), or
`--force` to overwrite the current version; creating needs neither. The CLI refuses a
blind update of an existing type with a usage error before sending anything.

## Entries

Slugs are built by the client from the name and checked by the server. A type slug is
**camelCase** (`blogPost`); a content slug is **kebab-case** (`hello-world`). Anything
else is refused with `INVALID_SLUG`.

An entry is `{id, type, slug, version, fields}`. The slug is stamped by the writer as
`_slug` and carries forward on update; an update sends fields, not identity.

```bash
coho entry create -t blogPost -s hello --file fields.json
coho entry create -t blogPost -s hello --set title.en-US=Hello --set rank=3
```

`--set path=value` sets a dotted path; the value is parsed as JSON when it parses
(`3`, `true`, `["a"]`, `{"x":1}`) and taken as a string otherwise. `--file` accepts a
path, `-` for stdin, or inline JSON.

Localized fields are objects keyed by locale. Locales have no registry; they are
whatever authors have used.

References are node ids as strings (`"author": "0192…"`; with `many`, an array).
Referential integrity is **not** enforced by the data tier: a dangling reference is
incomplete, not corrupt, and legal per-ref while a target waits to be merged.
`coho entry references ID` reports what links to an entry; `coho entry delete` shows
the count before asking.

Repeater items are objects with a server-assigned `_id`.

### Versions and ETags

Every write creates a version; the `ETag` on a read is that version's id, quoted.
`entry put` and `entry delete` must send it back as `If-Match`:

- `coho entry put ID --set …` reads first and writes with the ETag it read
  (read-modify-write). If somebody wrote in between, it fails with `VERSION_CONFLICT`.
- `coho entry put ID --file …` replaces the fields and needs `--if-match` or `--force`.
- `coho entry delete ID` reads then deletes the version it read (`--if-match` to pin).

A delete is a tombstone with its own ETag, never a physical removal. History
(`coho entry history ID`) includes it.

## Validation

Writes validate against the type as resolved **on the ref**. A failure is
`VALIDATION_FAILED` with `errors[]` of `{path, message}`, which the CLI prints one per
line. Merges re-validate against the target's schema.
