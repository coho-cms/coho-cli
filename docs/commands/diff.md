# diff

```
coho diff FROM [TO] [--absolute] [--fields]
```

`GET …/diff?from=FROM&to=TO&mode=…`. `TO` defaults to the current ref.

- `FROM` is the **target** side of a prospective merge (where `TO` would land).
- `TO` is the **source** — the branch under review.

Default mode `diverged` (three-dot) compares `TO` against the point the two diverged.
It also carries the merge preview: `conflicts` (what `merge TO --into FROM` would refuse
on) and a `mergeToken` to pass as `--expected-token` so the merge fails if the refs
move after review.

`--absolute` (two-dot) compares the tips and reports every change the target made that
the branch lacks, as though the branch reverted them — which is why it is not the
default.

```
from         v0.0.x
to           feature/pricing
mode         diverged
base         v0.0.x@42
added        1
modified     1
deleted      0
conflicts    1
merge token  eyJ…

CHANGE    KIND   SLUG     NODE
modified  entry  pricing  0192…
added     entry  cones    0193…

conflicts (merge will refuse until resolved):
SLUG     REASON  PATHS         NODE
pricing  field   title.en-US   0192…
```

`--fields` prints each field change with before/after. Paths are key-based at every
level: `title.en-US`, `sections[<uuid>].headline`. Content types also carry
`schemaChanges` with a `destructive` flag.

Conflict reasons: `field`, `deleted_and_modified`, `slug_collision`,
`internal_name_collision`, `unmatched`, `not_applicable`. `paths` is empty for
whole-node reasons.
