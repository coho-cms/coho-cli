# member

Account members and their **account-level** role (`admin` or `member`). Project roles
are a different thing: see [role](role.md).

| Command | Needs | What it does |
|---|---|---|
| `member list` | admin | `GET /api/v1/accounts/{id}/users` — id, name, email, role |
| `member role USER ROLE` | admin | change a member's role. `USER` is an id, or an email of a current member |
| `member remove USER` | admin | remove a member (asks; `-y` to skip) |
| `member leave` | login | remove yourself |

Refusals to know about:

- `LAST_ADMIN` (exit 1): demoting or removing the only admin while other members remain.
- `ACCOUNT_CLOSED`: no membership change on a closed account.
- `INSUFFICIENT_SCOPE`: the token was issued without `coho-auth/accounts`. Leaving
  needs only `coho-auth/self`.

Removal takes effect on the member's next request; bindings (actors) outlive
membership on purpose, so a re-added member keeps their history.
