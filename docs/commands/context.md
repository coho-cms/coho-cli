# use, status

## `coho use [ACCOUNT [PROJECT [REF]]] [--clear]`

Sets the sticky context for the current profile. Each argument is verified against the
server before it is saved:

- `ACCOUNT`: an account id or name from `/api/v1/me` (names are case-insensitive).
- `PROJECT`: a project id, or a name in the [local registry](../configuration.md#the-local-project-registry).
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

The current profile, URL and context. When the project is in the registry, its name is
shown beside the id.

```
profile  staging
url      https://staging.coho.example
account  0192b4…
project  0192c5…  (Marketing site)
ref      dev
```
