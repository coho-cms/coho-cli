# Install

Python 3.11 or newer.

## As a tool (recommended once published)

```bash
uv tool install coho-cli
# or
pipx install coho-cli
```

This gives you the `coho` command in an isolated environment. `coho-sdk` is pulled in
as a dependency.

## The library only

```bash
uv add coho-sdk            # in your project
pip install coho-sdk
pip install 'coho-sdk[keyring]'   # to read tokens the CLI stored in the OS keyring
pip install 'coho-sdk[testing]'   # coho_sdk.testing.FakeBff for your own tests
```

## From source

```bash
git clone https://github.com/coho-cms/coho-cli
cd coho-cli
uv sync
uv run coho --help
```

To have `coho` on your `PATH` from a checkout:

```bash
uv tool install --editable ./packages/coho-cli --with-editable ./packages/coho-sdk
```

## Shell completion

```bash
coho --install-completion        # bash, zsh, fish, PowerShell
```

## Verify

```bash
coho --version
coho configure --url https://coho.example.com    # your BFF
coho login --token "$TOKEN"                       # or `coho login` once an app client exists
coho whoami
```
