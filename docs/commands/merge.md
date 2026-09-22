# merge

```
coho merge [SOURCE] --into TARGET [-m MESSAGE] [--resolve FILE] [--expected-token T | --reviewed]
```

`POST …/merges`: a three-way merge of `SOURCE` (default: the current ref) into
`TARGET`. Requires `merge`. Lands whole or is refused whole — there is no partial
merge. Re-validates against the target's schema.

| Option | |
|---|---|
| `--into` | the target branch (required) |
| `-m/--message` | what this merge does. Write-once; there is no path to edit it |
| `--resolve` | resolutions JSON: a path, `-`, or inline |
| `--expected-token` | the `mergeToken` from the diff you reviewed; the merge is refused with `MERGE_REFS_MOVED` if the refs moved since |
| `--reviewed` | run the diff now and pass its token — "I looked at what this will do" |

Success prints `merged` (nodes written to the target), `unchanged`, `resolved`.

## Conflicts

When the store cannot settle a change, the merge is refused with `MERGE_CONFLICT`
(exit 4) and the conflicts are printed:

```
error MERGE_CONFLICT: The merge needs decisions a human has to make
conflicts:
  pricing: field at title.en-US
  hero: deleted_and_modified
```

With `-o json` the whole problem document is printed on stdout so a script can read
`conflicts[]`.

Answer them with a resolutions file, one per reported coordinate:

```json
[
  { "nodeId": "0192…", "path": "title.en-US", "take": "source" },
  { "nodeId": "0193…", "take": "target" },
  { "nodeId": "0194…", "path": "rank", "take": "value", "value": 7 }
]
```

- `take: source` — the branch being merged wins.
- `take: target` — the branch being merged into wins.
- `take: value` — a literal, only with a `path`.
- Omit `path` to settle the whole node.

Naming a side rather than repeating its content is what keeps a resolution from going
stale in its value, and it is the only form that can express **absence** — taking the
side that deleted a key. A resolution that does not apply is `MERGE_RESOLUTION_REJECTED`.

```
coho merge feature/pricing --into v0.0.x -m "New pricing" --resolve resolutions.json --reviewed
```

## What merge does not do

It does not tag (`coho tag create`) and does not promote (`coho promote`). Those are
separate decisions with separate permissions.
