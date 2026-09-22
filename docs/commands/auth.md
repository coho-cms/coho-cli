# login, logout, whoami, signup, configure, profile

See [authentication](../authentication.md) for how the flow works.

## `coho login`

```
coho login [--token TOKEN] [--no-browser] [--port N] [--timeout SECONDS]
```

Signs in to the current profile and stores the tokens. Without `--token`, runs the
browser PKCE flow: the profile needs `oidc_domain` and `client_id`. With `--token`,
stores the given access token as-is. Ends by calling `/api/v1/me` and printing who you
are, so a bad token fails here rather than on your next command.

| Option | |
|---|---|
| `--token` | store this bearer token; no browser |
| `--no-browser` | print the sign-in URL instead of opening it (SSH sessions) |
| `--port` | loopback port for the callback; must be registered on the app client. `0` picks a free port, which Cognito does not accept |
| `--timeout` | seconds to wait for the browser, default 300 |

Exit 3 if the provider refuses or the token does not work.

## `coho logout`

Deletes the stored tokens for the profile. Does not end sessions at the provider.

## `coho whoami`

`GET /api/v1/me`: your user, and each account with your role and actor id.

```
user     0192a3…
name     Ada Lovelace
email    ada@acme.example
profile  staging

ACCOUNT  ID       ROLE   ACTOR
Acme     0192b4…  admin  0192c5…
```

## `coho signup ACCOUNT_NAME [--name DISPLAY] [--no-browser]`

Starts founding a new account. The BFF finishes it in a browser (the flow ends with an
ID token the CLI never holds). When the page says you are signed in, run `coho login`.

## `coho configure`

```
coho [-p NAME] configure [--url URL] [--oidc-domain D] [--client-id ID] [--scopes "a b c"]
                         [--callback-port N] [--token-store keyring|file] [--use/--no-use]
```

Creates or updates the profile named by `-p` (default `default`) and, unless
`--no-use`, makes it current. Only the options given are changed. Prints the profile.

## `coho profile …`

| | |
|---|---|
| `profile list` | all profiles; `*` marks the current; `LOGIN` says `pkce` or `token` |
| `profile show [NAME]` | one profile's settings |
| `profile use NAME` | make it current |
| `profile delete NAME` | remove it and its stored tokens |
