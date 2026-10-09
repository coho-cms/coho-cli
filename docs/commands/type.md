# type

Content types as resolved on the current ref. See [content model](../content-model.md).

## `coho type list`

Slug, display name, field ids, version.

## `coho type get SLUG`

The type with its fields and **ETag**. `-o json` includes `etag`.

## `coho type put [SLUG] --file DEF [--if-match ETAG | --force] [--confirm-destructive]`

`PUT …/types/{slug}`. Requires `content:write`.

With no SLUG, the slug is built from `_name` in camelCase: `Blog post` becomes `blogPost`,
and `SEO description` becomes `seoDescription`. A name with no letters, or one that starts
with a digit, needs an explicit SLUG. The slug is fixed once the type exists. Renaming
`_name` with no SLUG therefore creates a second type. Pass the old slug to rename one.

`--file` is a path, `-` for stdin, or inline JSON, holding either the definition
(`{"_name": …, "fields": […]}`) or a wrapper `{"definition": …, "confirmDestructive": …}`.

- **Creating** needs no precondition.
- **Updating** needs `--if-match` with the ETag from `type get`, or `--force` to read
  the current ETag and overwrite. The CLI checks whether the type exists first and
  refuses a blind update with a usage error rather than letting the server answer 428.
- A **destructive** change (removing a field, narrowing a type, dropping a locale) is
  refused with `DESTRUCTIVE_SCHEMA_CHANGE` listing each change, unless
  `--confirm-destructive`. Prefer the two-phase ritual: `"omitted": true` first.

Refusals: `SCHEMA_INVALID`, `VERSION_CONFLICT`, `INTERNAL_NAME_CONFLICT`.

## `coho type delete SLUG [--confirm-destructive]`

Tombstones the type. Refused with `TYPE_IN_USE` (and the entry count) while entries
still resolve to it; `--confirm-destructive` orphans them deliberately. Asks first;
`-y` to skip.
