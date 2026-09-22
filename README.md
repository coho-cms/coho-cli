# coho-cli

The management CLI and Python SDK for **Coho**: log in once, set a context, and move
content through the pipeline with nouns everybody already knows.

```
coho login                                  # PKCE in a browser, tokens in the keyring
coho use acme                               # the account; then a project, then a ref
coho project create "Marketing site"        # trunk v0.0.x + dev/qa/stage/prod
coho type put blogPost --file blogPost.json
coho entry create -t blogPost -s hello --set title.en-US=Hello
coho branch create feature/pricing --use
coho diff v0.0.x                            # three-dot, conflicts included
coho merge --into v0.0.x -m "New pricing"
coho tag create v1.4.0 --branch v0.0.x -m "Q3 catalogue"
coho promote qa v1.4.0                      # waits for the snapshot unless --no-wait
coho rollback prod                          # the previous target, conditionally
coho key create --label site-prod --ref prod    # the delivery key, shown once
coho invite create jane@example.com --role member
```

Two distributions live in this repository:

| Package | What it is | Import / command |
|---|---|---|
| [`packages/coho-sdk`](packages/coho-sdk) | The library. CI scripts and notebooks import it directly. | `from coho_sdk import Coho` |
| [`packages/coho-cli`](packages/coho-cli) | The command. A thin layer over the library. | `coho` |

The CLI speaks to Coho's **BFF** with a person's bearer token, exactly like a browser
session does. It never sees an authoring credential, which is what makes it safe to
publish. The contracts it implements are vendored in [`contracts/`](contracts) at a
pinned commit of `coho-data`.

## Install

```bash
uv tool install coho-cli          # once published; see docs/install.md for from-source
```

## Documentation

Start with the [quickstart](docs/quickstart.md). Everything else is in [`docs/`](docs/index.md):

- **Guides:** [install](docs/install.md) · [authentication](docs/authentication.md) · [configuration and context](docs/configuration.md) · [concepts](docs/concepts.md) · [content model](docs/content-model.md) · [errors and exit codes](docs/errors.md) · [CI usage](docs/ci.md)
- **Command reference:** [`docs/commands/`](docs/commands/index.md), one page per noun
- **Library reference:** [`docs/library/`](docs/library/index.md)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) · [CHANGELOG.md](CHANGELOG.md)

## Status

Alpha. The command surface is complete for login, accounts, members, invitations,
projects, roles, refs, branches, tags, content types, entries, diff/merge,
environments, tiers, delivery keys, export and preview. Two things the server does
not yet offer are handled locally and flagged in the docs: project listing (a local
registry) and a public app client for the browser login (until it exists, use
`coho login --token`).

## Licence

Apache-2.0. See [LICENSE](LICENSE).
