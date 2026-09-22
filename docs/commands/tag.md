# tag

A tag is an immutable, undeletable `(branch, seq)` coordinate: at once a GC root, a
snapshot cache key and the rollback record.

## `coho tag list`

Tags are refs of kind `tag`; this is `coho ref list --kind tag`.

## `coho tag create NAME [--branch REF] [-m NOTES] [--at SEQ]`

`POST …/tags`. Requires `release:tag`. Only **version** branches can be tagged.

**Does not merge and does not validate.** A version branch tip is always valid, so a
tag has nothing left to check. Move content with `coho merge` first; the two are
independent verbs.

| Option | |
|---|---|
| `--branch` | the version branch. Default: the current ref |
| `-m/--description` | release notes; a list of tag names alone says nothing about what shipped |
| `--at` | tag at an explicit sequence, default the high-water mark. Bounded at both ends: above the high-water mark the tag would keep accruing content; below the branch's own creation it would contain nothing the branch wrote (`INVALID_TAG_POINT`) |

Names are free-form: `v1.4.0`, `2026.09.1` and `release-42` are equally valid. A
version convention is yours to enforce.

Warnings on stderr: `PENDING_FORWARD_PORT` — the branch holds nodes its successor
does not; tag time is when that omission becomes expensive.

There is no `tag delete`.
