# Install

Python 3.11 or newer. `uv` downloads one if you have none.

## As a tool (recommended)

```bash
uv tool install coho-cli
# or
pipx install coho-cli
```

This gives you the `coho` command in an isolated environment. `coho-management-sdk` is pulled in
as a dependency. The package is `coho-cli`: `coho` on PyPI is an unrelated project.

`uv tool upgrade coho-cli` (or `pipx upgrade coho-cli`) moves to the newest release.

## The library only

```bash
uv add coho-management-sdk                   # in your project
pip install coho-management-sdk
pip install 'coho-management-sdk[keyring]'   # read tokens the CLI put in the OS keyring
# coho_management_sdk.testing.FakeBff, for your own tests:
pip install 'coho-management-sdk[testing]'
```

## From source

```bash
git clone https://github.com/coho-cms/coho-management-sdk-python
git clone https://github.com/coho-cms/coho-cli
cd coho-cli
uv sync            # builds against the sibling SDK checkout
uv run coho --help
```

The CLI develops against a sibling checkout of the library. To build against the
published `coho-management-sdk` instead, run `uv sync --no-sources`.

To have `coho` on your `PATH` from a checkout:

```bash
uv tool install --editable . --with-editable ../coho-management-sdk-python
```

## Shell completion

```bash
coho --install-completion        # bash, zsh, fish, PowerShell
```

## Claude Code

This repository is also a Claude Code plugin: a skill that teaches Claude to use `coho`.
It reads `COHO.md` where a repository has one, starts from `coho status`, keeps to what
your role allows, leaves merging, tagging and promoting to you, and asks before anything
that changes who can do what or cannot be undone. Install the CLI first, then in Claude
Code:

```
/plugin marketplace add coho-cms/coho-cli
/plugin install coho@coho-cms
```

From a shell, `claude plugin marketplace add coho-cms/coho-cli` and
`claude plugin install coho@coho-cms` do the same. Claude uses the skill when a task
involves Coho, and `/coho:coho` invokes it by name. It pre-approves only commands that
read (`status`, `list`, `get`, `show`, `diff`, …); everything else asks your permission
as usual. Without plugins, copy [`skills/coho/`](../skills/coho/SKILL.md) to
`~/.claude/skills/coho/`.

Claude cannot sign in for you: run `coho login` yourself first. Then, in a repository
that works with a Coho project, `coho init --agents` writes `COHO.md` describing it: see
[coding agents](agents.md).

## Verify

```bash
coho --version
coho configure --url https://coho.example.com    # your BFF
coho login                                        # or --token "$TOKEN" for one obtained elsewhere
coho whoami
```
