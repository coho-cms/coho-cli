# Authentication

The BFF accepts `Authorization: Bearer <access token>` from the identity provider
(Cognito) and holds nothing for it: no session, no refresh, no CSRF. So the CLI
obtains and keeps the token itself.

## `coho login`

1. Starts a listener on `127.0.0.1:<callback_port>`.
2. Opens the hosted sign-in UI with PKCE (`code_challenge_method=S256`) and
   `redirect_uri=http://127.0.0.1:<port>/callback`.
3. Exchanges the code at `<oidc_domain>/oauth2/token` **without a client secret** — the
   CLI is a public client. The PKCE verifier is what proves this machine started the
   flow.
4. Stores the access token, refresh token and expiry in the OS keyring, one entry per
   profile (`service="coho"`, `username=<profile>`).
5. Calls `/api/v1/me` to confirm the token works, and prints who you are.

Before each request, the SDK refreshes the access token when it is within a minute of
expiry — the same margin the BFF uses for browser sessions — and stores the new one.

```
coho login                     # browser flow
coho login --no-browser        # print the URL to open elsewhere (SSH sessions)
coho login --port 9000         # a different loopback port, if the app client allows it
coho login --token "$TOKEN"    # store a token obtained elsewhere, no browser
coho logout                    # forget the stored tokens for the profile
coho whoami                    # /api/v1/me
```

### ⚠️ The callback URL must match exactly

Cognito compares `redirect_uri` byte for byte, port included. The CLI's app client
must be registered with `http://127.0.0.1:<callback_port>/callback` and the profile
must use the same port (`coho configure --callback-port 8765`; 8765 is the default).
There is no RFC 8252 "any loopback port" rule.

## The app client the CLI needs

`coho-data`'s `infra/auth` provisions one app client — the BFF's, confidential,
with a secret. The CLI needs a **second** one:

- public (no secret), authorization-code flow with PKCE,
- `explicit_auth_flows = ["ALLOW_REFRESH_TOKEN_AUTH"]`,
- callback `http://127.0.0.1:8765/callback`,
- scopes: `openid`, `coho-auth/self`, and — if the CLI should be able to invite
  members and change roles — `coho-auth/accounts`,
- its id added to `COHO_COGNITO_AUDIENCES`, or the auth tier refuses its tokens.

Which scopes it holds is an open decision in `coho-data` (doc 22 Q2). Without
`coho-auth/accounts`, `coho invite`, `coho member role`, `coho member remove`,
`coho account entitlements` and `coho account events` answer `INSUFFICIENT_SCOPE`.

**Until that client exists**, `coho login --token` is the path: obtain an access token
however your deployment allows and store it. The token still expires; there is no
refresh without a refresh token.

## Token storage

| Setting | Where tokens go |
|---|---|
| `token_store = "keyring"` (default) | The OS keyring via the `keyring` package: macOS Keychain, Windows Credential Locker, Secret Service on Linux |
| `token_store = "file"` | `<config dir>/credentials.json`, mode `0600` |

If the keyring is unusable (headless Linux without a Secret Service, the package
missing), the SDK silently falls back to the file. Set `--token-store file` explicitly
on a machine where you want that to be the rule.

## `COHO_ACCESS_TOKEN`

If set, this wins over anything stored: for CI, and as a stopgap. It carries a
**person's** identity — service accounts are not built yet — so scope it to the job and
rotate it. There is no refresh for a token supplied this way.

## Sign-up and invitations

Both finish in a browser, because they end with the BFF opening a session and posting
an ID token to the auth tier — a CLI never holds an ID token.

```
coho signup "Acme"                       # opens the sign-up page; then `coho login`
coho invite lookup <token-or-link>       # what the invitation offers; needs no login
coho invite accept <token-or-link>       # opens the acceptance page; then `coho login`
```

## What the CLI never holds

No `X-Coho-Actor`, no `externalId`, no OIDC client secret, no admin token. The BFF
chooses the actor for the account in the URL. That is the property that makes this
repository safe to publish.
