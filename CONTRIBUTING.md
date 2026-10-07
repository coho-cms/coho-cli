# Contributing

## Setup

The CLI is a thin layer over [`coho-management-sdk`](https://github.com/coho-cms/coho-management-sdk-python),
and develops against a sibling checkout of it:

```bash
git clone https://github.com/coho-cms/coho-management-sdk-python
git clone https://github.com/coho-cms/coho-cli
cd coho-cli
uv sync                    # resolves coho-management-sdk from ../coho-management-sdk-python
uv run coho --help
uv run pytest              # 22 tests, no network, no server
uv run ruff check . && uv run ruff format --check .
uv run mypy                # strict
```

Or `make check` for all of it.

### `coho` as a real command

To use your working copy as the installed `coho`, from any directory:

```bash
uv tool install --editable . --with-editable ../coho-management-sdk-python
```

The command lands in `~/.local/bin` and runs the source in both repositories, so
edits take effect at once. Reinstall, by adding `--force`, only when dependencies or
the entry point change; `uv tool uninstall coho-cli` removes it. It shares the
profiles and stored logins in `~/.config/coho` with `uv run coho`. `uv sync --no-sources` builds against the published
`coho-management-sdk` instead, which is what a user gets; see `[tool.uv.sources]` in
`pyproject.toml`.

## Layout

```
src/coho_cli/
  main.py          the typer app, global options, error → exit code
  _state.py        config/profile/client/context resolution for commands
  _output.py       tables, JSON, shown-once secrets
  _io.py           --file and --set parsing
  commands/        one module per noun
tests/             the whole command tree against the SDK's FakeBff
docs/              guides and the command reference
```

⚠️ **Push the SDK first.** CI builds the CLI against the SDK's `main` on GitHub,
not your local copy. A CLI change that uses new SDK code fails CI with
`"Coho" has no attribute …` until that SDK code is pushed; then re-run the CLI's
workflow.

The library, the API contracts and the library reference live in
[coho-management-sdk-python](https://github.com/coho-cms/coho-management-sdk-python).

## Rules of the road

1. **The library owns behaviour; the CLI owns presentation.** If a command needs logic
   that is not printing or argument parsing, it belongs in `coho_management_sdk` — open a pull
   request there and call it from here. Resist the urge to reimplement it locally.
2. **Errors print their `code`.** `main.py` maps `CohoError` to an exit code and a
   one-line message; never catch an error just to reword it.
3. **Secrets go to stdout alone**, with the warning on stderr, so
   `coho key create > key.txt` captures the key and nothing else.
4. **`--output json` prints the contract's response**, not a reshaped version of it.
   Every model in the SDK keeps `.raw` for exactly this.
5. **Tests run against `coho_management_sdk.testing.FakeBff`**, never a live server. A behaviour
   that needs a new route belongs in the fake, which means a pull request against the
   library.

## Releasing

The version comes from git tags (`hatch-vcs`); nothing in the source holds it.
Tag `v2026.1.0` to release, `v2026.1.0a1`, `b1` or `rc1` for a pre-release. Every
commit after a tag builds a dev version such as `2026.1.0a2.dev3`. ⚠️ Never tag a dev
version: CI refuses it, and every later build would fail.

1. Update the `coho-management-sdk` constraint if the CLI needs a newer library, and add
   a `CHANGELOG.md` entry.
2. Commit and push, then tag: `git tag v2026.1.0a4 && git push origin v2026.1.0a4`.
3. CI tests, builds a wheel and an sdist, fails if the tag is not a version in its
   standard form, uploads both as a build artifact, and attaches them to a GitHub
   Release, marked as a pre-release for an alpha, beta or release candidate.

Publishing to PyPI is off by default; the `publish-pypi` job runs only when the
repository variable `PUBLISH_TO_PYPI` is `true`, using a trusted publisher and the
`pypi` environment. Release `coho-management-sdk` first: a `coho-cli` that depends on a library
version nobody can install is not installable either.
