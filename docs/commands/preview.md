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
- `--limit` 1..100, default 25.

## `coho preview entry ID [--locale L]`

One entry as delivery would serve it. Printed as JSON.

Responses carry `Cache-Control: no-cache` because a live ref moves with every write.
