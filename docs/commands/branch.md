# branch

## `coho branch list`

Every branch with kind, status (`open`, `merged`, `archived`), parent, depth, and —
for a version branch — `pendingForwardPort`: how many nodes it holds that its
successor does not. Advisory; the loud version of that check runs at tag time.

## `coho branch create NAME [--from REF] [--version] [-m DESC] [--at SEQ] [--use]`

`POST …/branches`. O(1), copies nothing. Requires `branch:create`; `--version` cuts a
version branch and additionally requires `branch:create_version`.

| Option | |
|---|---|
| `--from` | a branch tip or a tag. Default: the current ref |
| `--version` | `kind: version_branch` (taggable) instead of `feature_branch` |
| `-m/--description` | up to 2000 characters |
| `--at` | branch at an explicit sequence. Not a timestamp. Rejected above the project's high-water mark and alongside a tag in `--from` |
| `--use` | make it the current ref |

Prints name, kind, source, `branchedAt` (the sequence), depth. A `depthWarning`
becomes a warning on stderr: resolution slows with depth (`BRANCH_TOO_DEEP` is the
hard stop).

Refusals: `REF_NAME_TAKEN`, `CANNOT_BRANCH_FROM`, `INVALID_BRANCH_POINT`,
`BRANCH_TOO_DEEP`, `FORBIDDEN`.

There is no delete. A merged branch shows `status: merged`.
