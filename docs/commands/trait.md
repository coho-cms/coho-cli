# trait

Traits as resolved on the current ref: named groups of fields, such as SEO or a social
card, that types take. A type names the traits it takes in its own `traits`; every entry
of it then has their fields. A trait is never a type: no entry is of one, and neither
`--type` nor a reference's `of` can name one. See [content model](../content-model.md).

## `coho trait list`

Slug, display name, field ids, the types that take it, and version.

## `coho trait get SLUG`

The trait with its fields and **ETag**. `-o json` includes `etag`.

## `coho trait put [SLUG] --file DEF [--if-match ETAG | --force] [--confirm-destructive]`

`PUT …/traits/{slug}`. Requires `content:write`.

`--file` holds `{"_name": …, "fields": […]}`, or a wrapper `{"definition": …}`, and
nothing else: a trait has no `extends`, `abstract`, `overrides` or `traits` of its own.
With no SLUG, the slug is built from `_name` in camelCase, as for `type put`.

- **Creating** needs no precondition; **updating** needs `--if-match` or `--force`.
- A trait's change reaches **every type that takes it, and every type below those**. Each
  must still be a valid type, or the change is refused with `SCHEMA_INVALID`. A change that
  would lose or invalidate their content is refused with `DESTRUCTIVE_SCHEMA_CHANGE`,
  listing each change and what it reaches (`reaches: page, servicePage, and 12 entries`),
  unless `--confirm-destructive`.

## `coho trait delete SLUG`

Tombstones the trait. Refused with `TRAIT_IN_USE`, naming the types, while any type takes
it, and no flag overrides that: a type whose trait is gone could not be read. Remove it
from those types' `traits` first. Asks first; `-y` to skip.
