# Using `coho` in CI

## Credentials

Create a project token for the job — the least role it needs — and store it as a CI
secret:

```bash
coho token create --role maintainer --label "GitHub Actions" --expires 90
```

```yaml
env:
  COHO_URL: https://staging.coho.example
  COHO_TOKEN: ${{ secrets.COHO_TOKEN }}
  COHO_ACCOUNT: 0192b4…   # ids, not names: a token cannot look names up
  COHO_PROJECT: 0192c5…
  COHO_OUTPUT: json
```

It overrides the keyring and needs no config file. It works only for that project's
content, expires (90 days by default, 365 at most), and `coho token revoke` stops it on
its next request. `coho token list` shows when each was last used.

## Output

`--output json` (or `COHO_OUTPUT=json`) prints the contract's response verbatim, so
`jq` works against the documented shapes:

```bash
coho entry list --all | jq -r '.entries[] | [.id, .slug] | @tsv'
coho diff v0.0.x feature/x | jq '.summary'
coho promote qa v1.4.0 | jq -r '.target'
```

Secrets: `coho key create` and `coho invite create` print the whole response in JSON
mode; in table mode only the secret goes to stdout and the warning to stderr, so
`coho key create > key.txt` captures the key alone.

## Exit codes

See [errors](errors.md). `4` means "re-read and retry" (`VERSION_CONFLICT`,
`MERGE_CONFLICT`, `ENVIRONMENT_MOVED`); a pipeline should treat it differently from `1`.

## Idempotency and safety

- `coho role grant` is a `PUT`: repeating it changes the role rather than stacking grants.
- `coho promote ENV TAG --expected CURRENT` makes a promotion conditional; use it whenever
  a pipeline decides based on an earlier read.
- `coho promote --no-wait` returns `SNAPSHOT_NOT_READY` (exit 1) instead of waiting;
  `--timeout` bounds the wait.
- `coho merge --reviewed` passes the diff's `mergeToken` so the merge fails with
  `MERGE_REFS_MOVED` if anything changed between review and merge.
- `-y` answers the confirmation prompts. Without it, a destructive verb on a
  non-interactive stdin aborts.

## A release job

```bash
set -euo pipefail
coho tag create "v$VERSION" --branch v0.0.x -m "$NOTES"
coho promote qa "v$VERSION" --timeout 600
coho preview entries --ref qa --limit 1 >/dev/null     # smoke: qa resolves
coho promote stage "v$VERSION"
```

## The library instead

For anything more than a few commands, import `coho_management_sdk` and skip the shell:

```python
from coho_management_sdk import Coho, SnapshotNotReady

coho = Coho(url=os.environ["COHO_URL"], token=os.environ["COHO_ACCESS_TOKEN"])
site = coho.account("acme").project(os.environ["COHO_PROJECT"])
site.tags.create(f"v{version}", branch="v0.0.x", description=notes)
site.environments.promote("qa", f"v{version}", wait=True, timeout=600)
```
