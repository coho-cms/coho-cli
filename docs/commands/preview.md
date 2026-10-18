# preview

The delivery contract, served live from authoring for the current ref, through the
BFF. This is what a website will see once the ref is published — the same shapes,
the same query parameters — without publishing it.

## `coho preview entries [-t TYPE] [--locale L] [--order FIELD] [--limit N] [--offset N]`

`GET …/preview/{ref}/entries`.

- `--locale` selects one locale's values; omit it and only non-localized fields come
  back (the same answer as a locale nobody has translated into).
- `--order` is any declared scalar field, `-` prefix for descending. `repeater` and
  `json` fields are neither sortable nor filterable.
- `--limit` 1..100, default 25. When more entries follow, the table ends with the
  `--offset` of the next page (in JSON, `hasMore`). There is no `--all`: each live page
  resolves the whole ref, so use [`entry list --all`](entry.md) to see everything.

## `coho preview entry ID [--locale L]`

One entry as delivery would serve it. Printed as JSON. `@SLUG` in place of the id
names the entry with that slug, as in [`entry`](entry.md).

Responses carry `Cache-Control: no-cache` because a live ref moves with every write.
