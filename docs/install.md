# Install

Python 3.11 or newer.

## As a tool (recommended once published)

```bash
uv tool install coho-cli
# or
pipx install coho-cli
```

This gives you the `coho` command in an isolated environment. `coho-management-sdk` is pulled in
as a dependency.

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

## Verify

```bash
coho --version
coho configure --url https://coho.example.com    # your BFF
coho login                                        # or --token "$TOKEN" for one obtained elsewhere
coho whoami
```
