# key

Delivery keys: what a website presents to read published content from the delivery
tier. Needs `delivery:keys`, seeded to `owner` alone — this is the only surface that
decides who *outside* the project may read what it has published.

## `coho key create [--label L] [--ref R …] [--expires-in-days N]`

`POST …/delivery-keys`. Prints, **once**:

```
id       0192…
label    site-prod
refs     prod
expires  2026-12-20T…
Delivery key
coho_dk_…
```

Only the hash is stored. Lose it and you issue another; there is no retrieval. The
warning goes to stderr, so `coho key create … > key.txt` captures the key alone; in
`-o json` mode the whole `{key, delivery}` response is printed.

- `--ref` (repeatable) limits the key to named refs. Omit for every ref in the project.
  An empty list is refused rather than meaning "everything".
- `--expires-in-days` 1..3650 bounds a leak nobody notices, which revocation cannot.

## `coho key list`

Metadata only — id, label, refs, created, expires — never the key or its hash. Plus
the public refs. Guarded as tightly as issuing, because the listing says who holds
access to what.

## `coho key revoke ID`

Delivery stops accepting the key within a few seconds (a global marker every
delivery instance polls), rather than at the end of a cache TTL. Asks; `-y` skips.

## `coho key public [ENV …]`

`PUT …/delivery-keys/public`: replaces the set of **environments** readable without a
key. No arguments clears it. Environment names only — the tag an open `prod` points at
stays key-required when addressed directly, or a release candidate nobody promoted
would be readable by whoever guessed its name.
