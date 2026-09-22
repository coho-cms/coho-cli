# Security

## Reporting

Email the maintainers privately rather than opening an issue. We will acknowledge
within three working days.

## What this tool holds

- **Access and refresh tokens** for the identity provider, per profile, in the OS
  keyring — or in `~/.config/coho/credentials.json` (mode 0600) when there is no
  keyring or the profile says `token_store = "file"`. `coho logout` removes them.
- **Nothing else that is a credential.** The CLI is a bearer caller; the BFF chooses the
  actor. There is no `X-Coho-Actor`, no `externalId`, no client secret.

## Things that are shown once

Delivery keys (`coho key create`) and invitation tokens (`coho invite create`) are
returned by the server exactly once and only their hash is stored. The CLI prints them
on stdout alone with the warning on stderr. Deliver invitation links over a channel that
does not leak; the token rides in the URL fragment, which browsers never send to
servers.

## `COHO_ACCESS_TOKEN`

Overrides the stored token. It carries a person's identity and is a stopgap for CI
until service accounts exist. Scope it to the job, rotate it, and never log it.
