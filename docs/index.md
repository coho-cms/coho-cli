# coho documentation

`coho` is a cross between `git` and `aws` for Coho. From `git`: a **context** that
sticks (account, project, ref) and nouns everybody knows — `branch`, `tag`, `diff`,
`merge`. From `aws`: **profiles** for named environments, `<noun> <verb> [--flags]`,
and `--output json` for scripts.

## Guides

| | |
|---|---|
| [Install](install.md) | uv, pipx, from source; shell completion |
| [Quickstart](quickstart.md) | login → project → type → entry → branch → merge → tag → promote, in ten minutes |
| [Authentication](authentication.md) | PKCE login, token storage, `COHO_ACCESS_TOKEN`, the app client the CLI needs |
| [Configuration and context](configuration.md) | `config.toml`, profiles, `coho use`, environment variables, the local project registry |
| [Concepts](concepts.md) | refs, branches, tags, environments, tiers, roles — what each is and who may touch it |
| [Content model](content-model.md) | type definitions, field types, entries, locales, references |
| [Errors and exit codes](errors.md) | branching on `code`, the catalogue, what the CLI exits with |
| [CI usage](ci.md) | running `coho` headless, JSON output, tokens, idempotency |

## Reference

- [Command reference](commands/index.md) — one page per noun
- [Library reference](https://github.com/coho-cms/coho-management-sdk-python/tree/main/docs) — `coho_management_sdk`, in its own repository

## Where things come from

The CLI talks only to Coho's **BFF** (`bff.yaml`), which relays the authoring surface
(`authoring.yaml`) as the caller's actor and a short allowlist of account-management
calls to the auth tier. The contracts are vendored in the
[library repository](https://github.com/coho-cms/coho-management-sdk-python/tree/main/contracts).
When this documentation and a contract disagree, the contract is right; please file an issue.
