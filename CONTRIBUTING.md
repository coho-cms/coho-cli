# Contributing

## Setup

```bash
uv sync                  # both packages, editable, plus dev tools
uv run coho --help
uv run pytest            # 65 tests, no network, no Docker
uv run ruff check packages && uv run ruff format --check packages
uv run mypy              # strict
```

Or `make check` for all of it.

## Layout

```
packages/coho-sdk/src/coho_sdk/     the library
  errors.py        CohoError and the branchable subclasses; error_for_response()
  transport.py     httpx, bearer header, problem+json → CohoError, ETag capture
  auth.py          PKCE login, token stores (keyring/file), refresh, TokenProvider
  profiles.py      ~/.config/coho/config.toml: profiles, context, project registry
  models.py        typed views over the contract's JSON (each keeps .raw)
  client.py        Coho → Account → Project → Ref, and the *Api classes
  testing.py       FakeBff: a contract-shaped fake for tests (yours too)
packages/coho-cli/src/coho_cli/     the command
  main.py          the typer app, global options, error → exit code
  _state.py        config/profile/client/context resolution for commands
  _output.py       tables, JSON, shown-once secrets
  commands/        one module per noun
contracts/         bff.yaml, authoring.yaml, delivery.yaml, PIN (coho-data commit)
docs/              guides, command reference, library reference
```

## Rules of the road

1. **The library owns behaviour; the CLI owns presentation.** If a command needs logic
   that is not printing or argument parsing, put it in `coho_sdk` and call it.
2. **Branch on `code`, never on status.** Add a subclass in `errors.py` only for codes a
   caller would plausibly `except`; everything else is a plain `CohoError` with an
   exact `.code`.
3. **Every model keeps `.raw`.** `--output json` prints the response as the contract
   describes it, not as our dataclass happens to spell it.
4. **Secrets are shown once and go to stdout alone**, with the warning on stderr, so
   `coho key create > key.txt` captures the key and nothing else.
5. **Tests run against `FakeBff`**, never a live server. If a behaviour depends on a
   contract detail, the fake should encode it (e.g. `If-Match` → 428/412).

## Contracts

`contracts/` is copied from `coho-data` at the commit in `contracts/PIN`. To bump:

```bash
make contracts COHO_DATA=../coho-data
```

Then read the diff and update `models.py`, `client.py`, the fake and the docs to
match. The pin bump is the release trigger.

## Releasing

Tag `v<sdk version>`; CI builds both wheels and publishes them. Bump the versions in
both `pyproject.toml` files and in `packages/coho-sdk/src/coho_sdk/_version.py`.
