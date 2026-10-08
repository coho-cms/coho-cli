# Authentication

The BFF accepts `Authorization: Bearer <access token>` from the identity provider
(Cognito) and holds nothing for it: no session, no refresh, no CSRF. So the CLI
obtains and keeps the token itself.

## `coho login`

1. Starts a listener on the loopback interface, port `callback_port`: on
   `127.0.0.1`, and on `::1` where the machine has it, since a browser may resolve
   `localhost` to either.
2. Opens Coho's sign-in pages with PKCE (`code_challenge_method=S256`) and
   `redirect_uri=http://localhost:<port>/callback`.
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
coho login --port 9000         # a different loopback port; any is accepted
coho login --token "$TOKEN"    # store a token obtained elsewhere, no browser
coho logout                    # forget the stored tokens for the profile
coho whoami                    # /api/v1/me
```

### Any loopback port

The sign-in service accepts `http://localhost:<any port>/callback` (and the same on
`127.0.0.1` and `[::1]`) for the CLI's client, as RFC 8252 asks of a native app, so
`coho login --port 9000` needs nothing registered anywhere. 8765 is only the default.

## The CLI's client

The CLI signs in through Coho's sign-in service, `auth-<env>.<domain>`
(`coho-data` doc 27), at the same `/oauth2/authorize` and `/oauth2/token` addresses
Cognito's hosted UI used before it was removed. Its client there, `coho-cli`, is:

- public, with no secret, since a program on a laptop cannot keep one; PKCE ties the
  code to the process that asked for it,
- refreshed through the sign-in service, whose refresh tokens only `coho-cli` can use,
- given `coho-auth/self` and `coho-auth/accounts` by the auth tier; `accounts` is what
  `coho invite` and `coho member role` need.

The tokens are still Cognito's, issued to the sign-in service's own Cognito client.

Point a profile at it:

```bash
coho configure --profile dev --url https://api-dev.coho-cms.dev \
    --oidc-domain https://auth-dev.coho-cms.dev --client-id coho-cli
```

`coho login --token` still works for a token obtained elsewhere. It has no refresh
token, so it lasts only as long as the access token does.

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
an ID token to the auth tier — a CLI never holds an ID token. None of these needs a
login, and none sends one.

```
coho signup "Acme"                       # opens the sign-up page; then `coho login`
coho invite lookup <token-or-link>       # what the invitation offers
coho invite accept <token-or-link>       # opens the acceptance page; then `coho login`
```

`coho signup` makes no API call at all: it opens the BFF's sign-up page, exactly as
`coho login` opens the sign-in page. Sign-up is an interactive browser session on
purpose, and before release that page is where a captcha is verified. You create your
identity and verify your email there, and the page ends by showing your new account.

## What the CLI never holds

No `X-Coho-Actor`, no `externalId`, no OIDC client secret, no admin token. The BFF
chooses the actor for the account in the URL. That is the property that makes this
repository safe to publish.
