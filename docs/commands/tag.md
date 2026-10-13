# tag

A tag is an immutable, undeletable `(branch, seq)` coordinate: at once a GC root, a
snapshot cache key and the rollback record.

## `coho tag list`

Tags are refs of kind `tag`; this is `coho ref list --kind tag`.

## `coho tag create NAME [--branch REF] [-m NOTES] [--at SEQ] [--validate]`

`POST …/tags`. Requires `release:tag`. Only **version** branches can be tagged.

**Does not merge, and validates only with `--validate`.** Writes and merges validate,
so a version branch tip is normally valid and a tag has nothing left to check. Move
content with `coho merge` first; the two are independent verbs.

| Option | |
|---|---|
| `--branch` | the version branch. Default: the current ref |
| `-m/--description` | release notes; a list of tag names alone says nothing about what shipped |
| `--at` | tag at an explicit sequence, default the high-water mark. Bounded at both ends: above the high-water mark the tag would keep accruing content; below the branch's own creation it would contain nothing the branch wrote (`INVALID_TAG_POINT`) |
| `--validate` | check every entry at the tag point first, and tag nothing if one fails. See below |

Names are free-form: `v1.4.0`, `2026.09.1` and `release-42` are equally valid. A
version convention is yours to enforce.

Warnings on stderr: `PENDING_FORWARD_PORT` — the branch holds nodes its successor
does not; tag time is when that omission becomes expensive.

There is no `tag delete`.

## Validating a release

"Normally valid" has a gap. A type written directly on a version branch does not
re-validate the entries already there, so a confirmed destructive change (a field made
required, a choice value dropped, a type deleted) can leave invalid entries behind, and
a tag cut over them ships them.

`--validate` checks every entry at the tag point: its fields against its type, its
links against what those fields admit, and that its type is still on the branch. It
costs the server a read of the whole branch. If any entry fails, the tag is refused
with `TAG_CONTENT_INVALID` (exit 1), nothing is tagged, and the name stays free:

```
error TAG_CONTENT_INVALID: 3 entries fail validation at the tag point. Correct them on
the branch and tag again; nothing was tagged.
3 invalid entries:
  about-us (page) 0192f3a4-5b6c-7d8e-9f01-23456789ab01
    $: required property 'layout' not found
  pricing (page) 0192f3a4-5b6c-7d8e-9f01-23456789ab02
    $: required property 'layout' not found
    $.code: does not match the regex pattern ^[a-z0-9-]+$
  spring-banner (no type) 0192f3a4-5b6c-7d8e-9f01-23456789ab03
    /: its content type is not on this ref
```

Each entry is shown with its type and its id, for `coho entry get`; `no type` means
its type is not on the branch, which is the failure itself. The server counts every
failure and lists the first 100 by slug; past that, a last line says how many were
listed, and running the command again once they are fixed shows the rest.

With `-o json` the whole problem document is printed on stdout instead, so a script
can read `entryCount` and `invalidEntries[]`.
