# env, promote, rollback

Environments are the refs that move. Each belongs to a tier, and repointing one needs
`promote:<tier>`.

## `coho env list`

Name, tier, `resolves` (`live` → branch tips; `snapshot` → tags), target.

## `coho env show NAME`

## `coho env create NAME --tier TIER [--target REF]`

`POST …/environments`. Needs `promote:<tier>` **of the tier it is created in**, not
`workflow:write`: you may only create environments in tiers you can already promote
to, so no environment operation confers a capability you lacked. The tier is fixed
forever. `LIVE_ENVIRONMENT_LIMIT` if the project is at its cap of live environments on
non-root branches.

## `coho promote ENV TARGET [--expected CURRENT] [-m REASON] [--no-wait] [--timeout S]`

`PUT …/environments/{env}` with `{target, expectedTarget, reason}`. Also available as
`coho env promote`.

- `TARGET` is a tag for a snapshot tier, a branch for a live tier
  (`INVALID_PROMOTION_TARGET` otherwise).
- `--expected` makes it conditional: only if the environment currently points there,
  else `ENVIRONMENT_MOVED` (exit 4). Use it whenever the decision was made from an
  earlier read.
- `-m` is recorded in the history as `reason`.
- A snapshot that is still building answers `SNAPSHOT_NOT_READY`; the CLI **waits** with
  a spinner, polling with backoff up to `--timeout` (default 300 s). `--no-wait` returns
  the error instead, for scripts that would rather poll themselves.

Prints the new and previous target. Warnings on stderr: `SKIPPED_TIER` (you promoted
past a tier — allowed, so the hotfix flow is legal), `PENDING_FORWARD_PORT`.

## `coho rollback ENV [-m REASON] [--no-wait]`

There is no rollback endpoint by design: a rollback is a promotion to a previous tag,
so the history shows a straight sequence of where the environment pointed. The CLI:

1. reads `env history`,
2. takes the entry before the current target,
3. shows `current → previous` and asks (`-y` skips),
4. issues `promote ENV previous --expected current`.

So if someone already fixed it forward, the rollback fails with `ENVIRONMENT_MOVED`
rather than undoing their work. `NO_PREVIOUS_TARGET` if there is nothing to go back to.

## `coho env unset NAME [-m REASON]`

Points the environment at nothing — a reachable state; `qa`, `stage` and `prod` start
there.

## `coho env delete NAME`

Allowed, unlike a tag: tags are the record, environments are the thing that moves.
The removal appears in the history rather than vanishing from it. Asks; `-y` skips.

## `coho env history NAME [--limit N] [--offset N]`

Where the environment has pointed, newest first: from, to, reason, actor, time. A `to`
of `(unset)` means it was unset or removed.
