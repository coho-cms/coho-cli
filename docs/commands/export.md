# export

```
coho export [REF] [--format ndjson|tar] [--out FILE|-] [--stream]
```

`GET …/refs/{ref}/export`. Requires `content:read`. `REF` defaults to the current ref
and must be a tag or a branch; environments and unset refs are `404`.

- **A tag** serves the image the build already wrote. By default the server answers
  `302` to a short-lived presigned URL; the CLI follows it and reports `via: presigned
  URL`. If the image was evicted, the server rebuilds it and answers
  `SNAPSHOT_NOT_READY`; run again shortly.
- **A branch** is computed at its current tip and not persisted. Because the tip
  moves, the sequence it was resolved at comes back in `X-Coho-Export-Seq` and is
  printed as `seq` — two people exporting an hour apart otherwise get different content
  while believing they are in sync. It is priced as authoring work.

| Option | |
|---|---|
| `--format` | `ndjson` (the image, one node per line) or `tar` |
| `--out` | output file, default `<ref>.<format>` with `/` replaced by `_`; `-` streams to stdout |
| `--stream` | force bytes through the API instead of a redirect, for networks that cannot reach the object store |

⚠️ Nothing exported is importable yet, and the manifest says so (`importable: false`).
