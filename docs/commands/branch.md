# branch

## `coho branch list`

Every branch with kind, status (`open`, `merged`, `changed`, `archived`), parent, depth,
and — for a version branch — `pendingForwardPort`: how many nodes it holds that its
successor does not. Advisory; the loud version of that check runs at tag time.

`changed` means merged, and written to since. With `-o json` that is `status: open`, as any
write reopens a branch, beside `changedSinceMerge: true`.

## `coho branch create NAME [--from REF] [--version] [-m DESC] [--at SEQ] [--no-use]`

`POST …/branches`. O(1), copies nothing. Requires `branch:create`; `--version` cuts a
version branch and additionally requires `branch:create_version`.

| Option | |
|---|---|
| `--from` | a branch tip or a tag. Default: the current ref |
| `--version` | `kind: version_branch` (taggable) instead of `feature_branch` |
| `-m/--description` | up to 2000 characters |
| `--at` | branch at an explicit sequence. Not a timestamp. Rejected above the project's high-water mark and alongside a tag in `--from` |
| `--no-use` | leave the current ref as it is. By default the new branch becomes the current ref |

Prints name, kind, source, `branchedAt` (the sequence), depth. A `depthWarning`
becomes a warning on stderr: resolution slows with depth (`BRANCH_TOO_DEEP` is the
hard stop).

The saved ref comes after `--ref` and `COHO_REF`, so while either is set, commands
keep using it. `branch create` warns when that hides the switch to the new branch.

Refusals: `REF_NAME_TAKEN`, `CANNOT_BRANCH_FROM`, `INVALID_BRANCH_POINT`,
`BRANCH_TOO_DEEP`, `FORBIDDEN`.

## `coho branch delete NAME [--confirm-destructive]`

`DELETE …/branches/NAME`. Requires `branch:create`, or `branch:create_version` for a version
branch. The branch stops resolving and its name is free again. The history of what was written
on it stays, so `coho entry history` reads the same, and an owner can bring it back with
[`coho ref restore`](ref.md). If it was the current ref, no ref is set afterwards.

A branch that has not been merged may hold the only copy of some work, so it asks a second
time. With `--yes` there is nobody to ask, so `--confirm-destructive` says it instead;
without it the refusal is `BRANCH_NOT_MERGED`. A merged branch needs neither.

Refusals: `BRANCH_IN_USE` for the trunk, and for a branch with branches cut from it, tags on
it, or an environment pointing at it; the message names them. `BRANCH_NOT_MERGED`,
`UNDER_LEGAL_HOLD`, `REF_NOT_FOUND`, `FORBIDDEN`.
