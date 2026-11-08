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

## `coho ref switch NAME`

Makes `NAME` the current ref: a branch, a tag or an environment of the current project.
It is checked against the server first, so a typo is `REF_NOT_FOUND` (exit 5) and the
saved ref stays as it was. The account and project are kept. Prints the ref, its kind
and target, then `Context ref is now NAME.`

```bash
coho merge feature/pricing --into v0.0.x -m "New pricing copy" --reviewed
coho ref switch v0.0.x        # back to the trunk
```

The saved ref comes after `--ref` and `COHO_REF`, so while either is set to another
ref, commands keep using it, and `ref switch` warns on stderr that it does.

## `coho ref describe NAME [DESCRIPTION] [--clear]`

Sets the standing description: what a branch is for, or release notes on a tag. The
name and a tag's coordinate stay immutable. Who may describe a ref is who may have
made it: `content:write` for a branch, `release:tag` for a tag, `promote:<tier>` for
an environment. Blank or `--clear` clears it.

## `coho ref deleted`

`GET …/deleted-refs`. Every deleted branch and tag, newest first, with what it was, when it went,
and anything that stands in the way of restoring it. Requires `ref:restore`, which a project owner
and an organization admin hold. `-o json` adds who deleted it and its description.

## `coho ref restore NAME [--as NEW] [--id ID]`

`POST …/deleted-refs/…/restore`. Brings back a deleted branch or tag. Requires `ref:restore`, and a
person: a project token is refused.

A branch comes back with its content, its description, and its status. If its name has been used
since, give it another with `--as`. A tag comes back under its own name, which nothing else has
held, and can be promoted to once its snapshot has rebuilt. `--id` chooses between deleted branches
that share a name.

Refusals: `RESTORE_BLOCKED` while the branch it was cut from is deleted too, or if `--as` would not
make a branch of the same kind. `REF_NAME_TAKEN`, `REF_NOT_FOUND`, `FORBIDDEN`.
