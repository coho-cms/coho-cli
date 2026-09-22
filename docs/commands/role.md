# role

Project roles — who may do what in the current project. Needs `role:grant`, seeded
to `owner` alone; account admins hold implied owner.

## `coho role list`

`GET …/roles`: actor id, role, who granted it, when. The content tier stores **ids,
never names** (it must not become a directory); the CLI fills in `WHO` for your own
actor only. To map the rest, `coho account list` shows your actor per account and
`coho member list` shows users — an actor id is per (user, account).

## `coho role grant ACTOR ROLE`

`PUT …/roles/{actorId}` with one of `viewer`, `author`, `maintainer`,
`release_manager`, `owner`. A `PUT` because the outcome is a state: repeating it
changes the role rather than stacking a second grant. `ACTOR` may be `me`.

Refused for an actor who is not a member of the project's account (`BAD_REQUEST`):
such a grant would count for nothing.

## `coho role revoke ACTOR`

Removes this project's grant and nothing else. An account admin still reaches the
project through implied owner; taking that away is an account-role change
(`coho member role`).

## `coho role ladder`

Prints the seeded ladder:

| Role | Permissions |
|---|---|
| `viewer` | `content:read` |
| `author` | + `content:write`, `branch:create` |
| `maintainer` | + `merge`, `release:tag`, `promote:dev`, `promote:qa` |
| `release_manager` | + `promote:stage`, `promote:prod`, `branch:create_version` |
| `owner` | all, including `role:grant`, `delivery:keys`, `workflow:write` |

There is no "a project must keep an owner" rule: an account admin can always repair a
project's grants.
