# Configuration and context

## The file

`~/.config/coho/config.toml` (mode `0600`), or `$XDG_CONFIG_HOME/coho/config.toml`, or
`$COHO_CONFIG_DIR/config.toml`.

```toml
[context]
profile = "staging"                       # which profile commands use by default

[profiles.staging]
url = "https://staging.coho.example"      # the BFF
oidc_domain = "https://acme.auth.us-east-1.amazoncognito.com"
client_id = "1h57kf5cpq17m0eml12EXAMPLE"  # the CLI's public app client
scopes = ["openid", "coho-auth/self", "coho-auth/accounts"]
callback_port = 8765                      # must match the app client's callback URL: http://localhost:8765/callback
token_store = "keyring"                   # or "file"

[profiles.staging.context]
account = "0192b4…"                       # account id
project = "0192c5…"                       # project id
ref = "dev"

[profiles.staging.projects."0192b4…"]     # keyed by account id: the local registry
"Marketing site" = "0192c5…"

[profiles.local]
url = "http://localhost:8090"
token_store = "file"
```

Tokens are **not** in this file. See [authentication](authentication.md).

## Profiles

A profile is a named environment: one BFF and one way to get a token for it.

```
coho configure --profile staging --url https://staging.coho.example \
    --oidc-domain … --client-id … [--scopes "…"] [--callback-port 8765] [--token-store file]
coho profile list
coho profile show [NAME]
coho profile use NAME
coho profile delete NAME          # also forgets its stored tokens
coho -p NAME <command>            # one-off
COHO_PROFILE=NAME coho <command>
```

The first profile you configure becomes the current one; `--no-use` prevents that.

## Context

Three values stick per profile: account, project, ref. Set them once:

```
coho use <account>                         # by name or id
coho use <account> <project>               # by id, or by a name the registry knows
coho use <account> <project> <ref>
coho use --clear
coho status
```

Each argument is **verified against the server** before it is saved, so a typo fails
now. Changing the account clears the project and ref; changing the project clears the
ref.

Resolution order, highest first:

1. `--account`, `--project`, `--ref` on the command line
2. `COHO_ACCOUNT`, `COHO_PROJECT`, `COHO_REF`
3. the profile's saved context

A command that needs a value none of these provide is a usage error (exit 2) naming
the flag and the `use` command.

`coho project create` and `coho branch create --use` update the context for you.

## The local project registry

⚠️ The server has no "list projects" endpoint yet (`coho-data` doc 04 §9 explains why:
tenancy). So the CLI keeps a **per-profile, per-account** table of the projects it has
seen: created with `project create`, opened with `use` or `project show`, or added
with `project register`.

```
coho project list                          # what this CLI knows, locally
coho project register <id> [NAME]          # check it exists, then remember it
coho project forget <name-or-id>           # local only
```

Names in the registry are accepted anywhere a project is expected, including `--project`
and `COHO_PROJECT`. When the server gains a listing, `project list` will use it and the
registry becomes a cache.

## Environment variables

| Variable | Effect |
|---|---|
| `COHO_PROFILE` | profile to use |
| `COHO_URL` | override the profile's BFF URL |
| `COHO_ACCOUNT`, `COHO_PROJECT`, `COHO_REF` | override the context |
| `COHO_ACCESS_TOKEN` | use this bearer token, ignoring the store |
| `COHO_OUTPUT` | `table` or `json` |
| `COHO_CONFIG_DIR` | where `config.toml` and `credentials.json` live |

## Global options

```
-p, --profile NAME     -o, --output table|json     --url URL
--account X  --project X  --ref X                  -q, --quiet   -y, --yes
-V, --version          -h, --help
```

`--yes` skips the confirmation prompts that destructive verbs ask (`entry delete`,
`member remove`, `env delete`, `key revoke`, `rollback`). `--quiet` suppresses the
one-line confirmations on stdout; errors still go to stderr.
