# coho-cli

The management CLI and Python SDK for **Coho**: log in once, set a context, and move
content through the pipeline with nouns everybody already knows.

```
coho login                                  # PKCE in a browser, tokens in the keyring
coho use acme                               # the account; then a project, then a ref
coho project create "Marketing site"        # trunk v0.0.x + dev/qa/stage/prod
coho type put blogPost --file blogPost.json
coho entry create -t blogPost -s hello --set title.en-US=Hello
coho branch create feature/pricing          # and switches to it
coho diff v0.0.x                            # three-dot, conflicts included
coho merge --into v0.0.x -m "New pricing"
coho tag create v1.4.0 --branch v0.0.x -m "Q3 catalogue"
coho promote qa v1.4.0                      # waits for the snapshot unless --no-wait
coho rollback prod                          # the previous target, conditionally
coho key create --label site-prod --ref prod    # the delivery key, shown once
coho invite create jane@example.com --role member
```

This repository holds the **command**. It is a thin layer over
[`coho-management-sdk`](https://github.com/coho-cms/coho-management-sdk-python), the
Python library, which lives in its own repository along with the API contracts both
implement — so a script can import the library without installing a CLI.

| | Repository | Import / command |
|---|---|---|
| The command | [coho-cms/coho-cli](https://github.com/coho-cms/coho-cli) | `coho` |
| The library | [coho-cms/coho-management-sdk-python](https://github.com/coho-cms/coho-management-sdk-python) | `from coho_management_sdk import Coho` |

The CLI speaks to Coho's **BFF** with a person's bearer token, exactly like a browser
session does. It never sees an authoring credential, which is what makes it safe to
publish.

## Install

```bash
uv tool install coho-cli          # or: pipx install coho-cli
```

Python 3.11 or newer; `uv` downloads one if you have none. The package is `coho-cli`:
`coho` on PyPI is an unrelated project. [Install](https://github.com/coho-cms/coho-cli/blob/HEAD/docs/install.md)
covers building from source.

## Documentation

Start with the [quickstart](https://github.com/coho-cms/coho-cli/blob/HEAD/docs/quickstart.md). Everything else is in [`docs/`](https://github.com/coho-cms/coho-cli/blob/HEAD/docs/index.md):

- **Guides:** [install](https://github.com/coho-cms/coho-cli/blob/HEAD/docs/install.md) · [authentication](https://github.com/coho-cms/coho-cli/blob/HEAD/docs/authentication.md) · [configuration and context](https://github.com/coho-cms/coho-cli/blob/HEAD/docs/configuration.md) · [concepts](https://github.com/coho-cms/coho-cli/blob/HEAD/docs/concepts.md) · [content model](https://github.com/coho-cms/coho-cli/blob/HEAD/docs/content-model.md) · [errors and exit codes](https://github.com/coho-cms/coho-cli/blob/HEAD/docs/errors.md) · [CI usage](https://github.com/coho-cms/coho-cli/blob/HEAD/docs/ci.md)
- **Command reference:** [`docs/commands/`](https://github.com/coho-cms/coho-cli/blob/HEAD/docs/commands/index.md), one page per noun
- **Library reference:** [coho-management-sdk-python/docs](https://github.com/coho-cms/coho-management-sdk-python/tree/HEAD/docs) — for using `coho_management_sdk` directly
- **Contributing:** [CONTRIBUTING.md](https://github.com/coho-cms/coho-cli/blob/HEAD/CONTRIBUTING.md) · [SECURITY.md](https://github.com/coho-cms/coho-cli/blob/HEAD/SECURITY.md) · [CHANGELOG.md](https://github.com/coho-cms/coho-cli/blob/HEAD/CHANGELOG.md)

## Status

Alpha. The command surface is complete for login, accounts, members, invitations,
projects, roles, refs, branches, tags, content types, entries, diff/merge,
environments, tiers, delivery keys, export and preview. Two things the server does
not yet offer are handled locally and flagged in the docs: project listing (a local
registry).

## Licence

Apache-2.0. See [LICENSE](https://github.com/coho-cms/coho-cli/blob/HEAD/LICENSE).
