# ref

Branches, tags and environments share one namespace.

## `coho ref list [--kind KIND]`

Every ref with its kind, target and description. `--kind` filters to
`version_branch`, `feature_branch`, `tag` or `environment`.

```
REF              KIND            TARGET      DESCRIPTION
v0.0.x           version_branch  -           -
feature/pricing  feature_branch  -           New pricing copy
v1.0.0           tag             v0.0.x@42   First release
dev              environment     v0.0.x      -
prod             environment     v1.0.0      -
qa               environment     -           -
```

An **unset** environment is listed with no target: the ref exists, it points nowhere
yet. The same ref is a `404` on content endpoints, because there is nothing to resolve.

## `coho ref show [NAME]`

One ref. Default: the current ref.

## `coho ref describe NAME [DESCRIPTION] [--clear]`

Sets the standing description: what a branch is for, or release notes on a tag. The
name and a tag's coordinate stay immutable. Who may describe a ref is who may have
made it: `content:write` for a branch, `release:tag` for a tag, `promote:<tier>` for
an environment. Blank or `--clear` clears it.
