# type

Content types as resolved on the current ref. See [content model](../content-model.md).

## `coho type list`

Slug, display name, field ids, version.

## `coho type get SLUG`

The type with its fields and **ETag**, the type it extends, the traits it takes, and
whether it is abstract. `-o json` includes `etag`. The fields are the type's own, as it
declares them; `-o json` with the API's `?resolve=effective` (`types.get(…, effective=True)`
in the library) has every field it has, inherited or from a trait, each with `from`.

## `coho type put [SLUG] --file DEF [--if-match ETAG | --force] [--confirm-destructive]`

`PUT …/types/{slug}`. Requires `content:write`.

With no SLUG, the slug is built from `_name` in camelCase: `Blog post` becomes `blogPost`,
and `SEO description` becomes `seoDescription`. A name with no letters, or one that starts
with a digit, needs an explicit SLUG. The slug is fixed once the type exists. Renaming
`_name` with no SLUG therefore creates a second type. Pass the old slug to rename one.

`--file` is a path, `-` for stdin, or inline JSON, holding either the definition
(`{"_name": …, "fields": […]}`) or a wrapper `{"definition": …, "confirmDestructive": …}`.
A definition may name a parent, `"extends": "page"`, whose fields it has; be `"abstract":
true`, taking no entries of its own; take traits, `"traits": ["seo"]`, whose fields it has
too; and tighten what it inherits or takes under `"overrides": {"title": {"max": 120}}`.
A field id may come from one place only.

- **Creating** needs no precondition.
- **Updating** needs `--if-match` with the ETag from `type get`, or `--force` to read
  the current ETag and overwrite. The CLI checks whether the type exists first and
  refuses a blind update with a usage error rather than letting the server answer 428.
- A **destructive** change (removing a field, narrowing a type, dropping a locale) is
  refused with `DESTRUCTIVE_SCHEMA_CHANGE` listing each change, unless
  `--confirm-destructive`. Prefer the two-phase ritual: `"omitted": true` first.

Refusals: `SCHEMA_INVALID`, `VERSION_CONFLICT`, `INTERNAL_NAME_CONFLICT`, `FIELD_INHERITED`
(a field declared again, or loosened, rather than tightened under `overrides`), and
`FIELD_CONFLICT` (a field id from two places: a trait and the parent, two traits, or a
trait and the type).

## `coho type delete SLUG [--confirm-destructive]`

Tombstones the type. Refused with `TYPE_IN_USE` (and the entry count) while entries
still resolve to it; `--confirm-destructive` orphans them deliberately. Asks first;
`-y` to skip.
