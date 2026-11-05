# use, status

## `coho use [ACCOUNT [PROJECT [REF]]] [--clear]`

Sets the sticky context for the current profile. Each argument is verified against the
server before it is saved:

- `ACCOUNT`: an account id or name from `/api/v1/me` (names are case-insensitive).
- `PROJECT`: a project id, or its name: the [local registry](../configuration.md#the-local-project-registry) answers first, then the projects the server lists for you. Names are unique in an account, ignoring case.
  The project is fetched, and its name is recorded in the registry.
- `REF`: a branch, tag or environment; fetched with `GET …/refs/{ref}`.

Changing the account clears the project and ref; changing the project clears the ref.
Prints the resulting status. `--clear` forgets all three.

```
coho use acme
coho use acme "Marketing site" dev
coho use acme 0192c5… feature/pricing
```

## `coho status`

The current profile and URL, the credential in use, the context, and what that
credential may do there: your role in the account and in the project, and the project
role's permissions. It answers before you try, which suits a script or an AI agent
deciding what to attempt. When the project is in the registry, its name is shown beside
the id.

```
profile       staging
url           https://staging.coho.example
credential    ada@acme.example, from coho login, refreshed as needed
account       Acme (0192b4…)
account role  admin
project       Marketing site  (0192c5…)
project role  owner (as an account admin)
ref           dev
permissions   everything (*)
```

With a project token (`COHO_TOKEN`), the credential is the token, and the project role
is the token's:

```
credential    project token "GitHub Actions", from COHO_TOKEN, expires 2027-02-02
project role  maintainer (the token's)
permissions   content:read, content:write, branch:create, promote:preview, merge, release:tag, promote:dev, promote:qa
```

`--output json` (the default when stdout is not a terminal) gives the same as fields:

| Field | |
|---|---|
| `credential` | `null` when there is none; else `kind` (`person` or `project_token`) and `source`: `COHO_TOKEN`, `COHO_ACCESS_TOKEN`, `login` (from `coho login`, refreshed), or `stored` (from `coho login --token`, not refreshed). A person adds `user`, `name`, `email`; a token adds `id`, `label`, `expiresAt`, `account`, `accountName`, `project`, `projectName`. No `user` or `id` means the server did not accept the credential |
| `accountRole` | `admin` or `member`; `null` for a project token, which holds no account role |
| `projectRole` | `viewer`, `author`, `maintainer`, `release_manager`, or `owner`; an account admin is `owner` of every project |
| `permissions` | the project role's permissions (see `coho role ladder`); `["*"]` for `owner`, which holds all of them; `[]` where the credential may do nothing, such as a project token pointed at another project; `null` with no project in the context, or no credential |

Each lookup is best effort: signed out, offline, or a context the credential cannot see
leaves its fields `null`, and `status` still answers.
