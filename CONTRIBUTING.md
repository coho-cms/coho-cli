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
  _browser.py      whether there is a browser here; opening one or printing the URL
  _agents.py       `coho init --agents`: COHO.md and the AGENTS.md/CLAUDE.md block
  commands/        one module per noun
tests/             the whole command tree against the SDK's FakeBff
docs/              guides and the command reference
skills/coho/       the Claude Code skill; .claude-plugin/ makes the repository a plugin
```

⚠️ **Push the SDK first.** CI builds the CLI against the SDK's branch of the same version
(`v2026.2.1`, set in `.github/workflows/ci.yml`) on GitHub,
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
Tag `release-v2026.2.1` to release, `release-v2026.2.1a1`, `b1` or `rc1` for a
pre-release. Every commit after a tag builds a dev version such as `2026.2.1a2.dev3`.

⛔ **`release-v`, never a bare `v`.** The branch is named `v2026.2.1`, so a tag of
that name is a second ref of that name: `git push origin v2026.2.1` is refused as
ambiguous, and with two version tags on one commit `git describe` may pick the older
one, building a wheel whose version does not match the tag — which CI refuses, as it
did on 2026-11-05. `git_describe_command` in `pyproject.toml` matches `release-v*`
only, so the old `v*` tags cannot be chosen.

Every Coho repository works towards one shared version, on a branch named for it:
start a new version by cutting that branch here and in the SDK, and move CI's SDK
`ref:` to it. ⚠️ Never tag a dev version: CI refuses it, and every later build would
fail.

1. Update the `coho-management-sdk` constraint if the CLI needs a newer library, and add
   a `CHANGELOG.md` entry.
2. Commit and push, then tag: `git tag -a release-v2026.2.1a2 -m "2026.2.1a2: …" &&
   git push origin refs/tags/release-v2026.2.1a2`.
3. CI tests, builds a wheel and an sdist, fails if the tag is not a version in its
   standard form, uploads both as a build artifact, attaches them to a GitHub
   Release (a pre-release for an alpha, beta or release candidate), and publishes
   them to [PyPI](https://pypi.org/project/coho-cli/).

⚠️ **Release `coho-management-sdk` first**, and wait until it is on PyPI: a `coho-cli` that
depends on a library version nobody can install is not installable either. PyPI never
takes the same version's files twice, even after a delete, so a broken release is fixed
by the next tag.

The `publish-pypi` job authenticates as a [trusted publisher](https://docs.pypi.org/trusted-publishers/)
with a short-lived OIDC token, so no API token is stored anywhere, and deploys through
the `pypi` environment, which only `v*` tags can use. Setting the repository variable
`PUBLISH_TO_PYPI` to anything but `true` turns it off.

## Windows packages

On every build, CI freezes `coho` with PyInstaller (`packaging/pyinstaller/`). The
`windows-installer` job then packages the frozen folder with `packaging/windows/build.ps1`:

- `coho-<version>-windows-x64.zip`, the folder as it is;
- `coho-<version>-windows-x64.msi`, which installs into `C:\Program Files\Coho CLI` and
  adds that folder to the system `PATH`.

`test-install.ps1` then installs the MSI on the runner, checks that `coho` resolves from
the machine `PATH` and reports the right version, and uninstalls it. On a release tag,
the `release` job attaches both files, plus `coho-<version>-winget-manifests.zip` from
`winget_manifest.py`.

WiX only runs on Windows, so the MSI can only be built in CI or on a Windows machine. The
Python halves, `msi_version.py` and `winget_manifest.py`, are tested with the rest of the
suite in `tests/test_windows_packaging.py`.

### Versions and codes

Windows Installer versions are `major.minor.build`, with major at most 255.
`msi_version.py` drops the century, so 2026.2.4 installs as 26.2.4. A pre-release adds a
fourth field, which Windows Installer ignores: 2026.2.4rc1 is 26.2.4.501. The MSI allows
upgrades within the same version, so the final replaces its release candidate. Every
version gets its own `ProductCode`, derived from the version string.

⛔ **Never change `UPGRADE_CODE`** in `msi_version.py`, or the GUID of the `PathEntry`
component in `coho.wxs`. The upgrade code is what makes a new MSI replace the old CLI. With
a different one, users end up with two Coho CLIs, each holding a `PATH` entry.

### WiX and its maintenance fee

The MSI is built with WiX v7 (`$WixVersion` in `build.ps1`). WiX v7 runs only once its Open
Source Maintenance Fee EULA (`wix7`) is accepted, so `build.ps1` accepts it on Coho's
behalf. Scott agreed to that on 2026-11-19. The EULA requires sponsoring the
[wixtoolset GitHub organization](https://github.com/sponsors/wixtoolset) once Coho's
revenue passes US$10,000 a year: [the terms](https://docs.firegiant.com/wix/osmf/). A new
WiX major brings a new EULA id, so read its terms before bumping `$WixVersion`.

### Signing

`coho.exe` and the MSI are unsigned until signing is set up. Until then SmartScreen warns
on first run, and winget's own checks are harder to pass. Signing uses
[Azure Artifact Signing](https://learn.microsoft.com/en-us/azure/artifact-signing/),
formerly Trusted Signing, in the `windows-installer-signed` job. That job replaces
`windows-installer` on release tags once it is turned on. It authenticates with OIDC,
so no Azure secret is stored in GitHub.

1. **Azure.** In a paid subscription (free and trial ones are refused), register the
   `Microsoft.CodeSigning` resource provider. Create an Artifact Signing account. Its
   region sets the endpoint: East US is `https://eus.codesigning.azure.net/`.
2. **Identity validation.** In the account, request *Public* identity validation for the
   organization. Microsoft checks the legal name, address, and registration, which can
   take from hours to several business days. The certificates name this organization.
3. **Certificate profile.** Once validation passes, create a *Public Trust* certificate
   profile from it.
4. **An identity for CI.** Register an app in Microsoft Entra ID, or create a
   user-assigned managed identity. Add a federated credential: *GitHub Actions*,
   organization `coho-cms`, repository `coho-cli`, entity *Environment*, name
   `windows-signing`. On the certificate profile, give the identity the *Artifact Signing
   Certificate Profile Signer* role.
5. **GitHub.** Create the `windows-signing` environment, with a deployment rule that
   allows tags matching `release-v*` and nothing else. Give it these variables (none is
   secret): `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`,
   `ARTIFACT_SIGNING_ENDPOINT`, `ARTIFACT_SIGNING_ACCOUNT`, and `ARTIFACT_SIGNING_PROFILE`.
6. **Turn it on.** Set the repository variable `WINDOWS_SIGNING` to `true`. It has to be a
   repository variable, not an environment one, because the job's `if:` reads it before
   any environment applies. The next release tag signs. To check without a release, tag a
   pre-release such as `release-v2026.2.5a1`.

The Basic plan is US$9.99 a month for 5,000 signatures, and each release uses two.

### Submitting to winget

[winget](https://github.com/microsoft/winget-pkgs) takes packages by pull request. The
manifests name the MSI on the GitHub release by URL and SHA-256, so submit only a final
release, after its assets are attached.

1. Download `coho-<version>-winget-manifests.zip` from the release and unzip it. It holds
   `manifests/c/CohoCMS/CLI/<version>/`.
2. On Windows, check them: `winget validate --manifest <that folder>`. Then try an install:
   run `winget settings --enable LocalManifestFiles` once from an elevated terminal, then
   `winget install --manifest <that folder>`.
3. Fork `microsoft/winget-pkgs`, copy the folder to the same path in the fork, and open a
   pull request with the PR template's checklist filled in. Bots install the package in a
   sandbox and scan it, and a moderator merges it, usually within a few days. Watch the
   pull request for questions from the bots.

The first pull request fixes the identifier `CohoCMS.CLI` for good. Later versions repeat
the same steps with a new folder. Automating that submission from the `release` job, with
`wingetcreate` or `komac` and a token for a fork, is not built yet.
