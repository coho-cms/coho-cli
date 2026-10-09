# token

Project tokens: credentials for automation (`coho-data` doc 29). A token holds **one
role in one project** — `viewer`, `author`, `maintainer` or `release_manager`, never
`owner` — and works only for that project's content. All three commands need `owner`
on the current project.

## `coho token create --role ROLE --label LABEL [--expires DAYS]`

`POST …/projects/{project}/tokens`. `--expires` is 1–365 days, 90 by default; every
token expires. ⚠️ The token (`coho_pt_…`) is printed once: only its hash is stored.

A token belongs to the project, not to you: it keeps working if you leave the account,
until it expires or an owner revokes it.

## `coho token list`

Every token, revoked and expired ones included, with its role, state, expiry and when
it was last used. A token's id is what it signs content with, so this list is how you
read who made a change in the history.

## `coho token revoke ID`

Stops it on its next request. Revoking twice is not an error.
