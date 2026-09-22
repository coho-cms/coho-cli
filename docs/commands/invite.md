# invite

Invitations into the current account. Coho does **not** send email: the admin who
creates an invitation gets the token once and owns delivering it.

## `coho invite create EMAIL [--role member|admin] [--link|--token]`

Needs admin and the `coho-auth/accounts` scope. Prints, once:

```
invitation  0192f1…
email       jane@acme.example
role        member
expires     2026-09-29T00:00:00Z
Invitation link
https://staging.coho.example/invite#eyJ…
```

The token rides in the URL **fragment**, which browsers never send to servers, so the
link can be pasted into a chat without the token appearing in anybody's access log.
`--token` prints the bare token instead. The warning that it is shown once goes to
stderr, so `coho invite create … > link.txt` captures the link alone. In `--output json`
mode the whole response (`{invitation, token}`) is printed.

Refusals: `PLAN_LIMIT` (member cap, checked at invite time and again at acceptance),
`INVALID` (role or email), `ACCOUNT_CLOSED`.

## `coho invite list [--all]`

Pending invitations; `--all` includes accepted, revoked and expired. Status is derived
in that precedence order.

## `coho invite revoke INVITATION`

By id, or by the invited email (the pending one). Revoking an already-accepted
invitation answers `INVITATION_ACCEPTED`.

## `coho invite lookup TOKEN_OR_LINK`

What an invitation offers — account, role, expiry — without signing in. Holding the
token is the credential. Accepts the whole link; the fragment is extracted.

## `coho invite accept TOKEN_OR_LINK [--name DISPLAY] [--no-browser]`

Starts acceptance. The BFF holds the token server-side and finishes in a browser with
the identity provider (the email must be verified by the provider and match the
invited address, else `EMAIL_NOT_VERIFIED` / `INVITATION_EMAIL_MISMATCH`). When the
page says you are signed in, run `coho login`.
