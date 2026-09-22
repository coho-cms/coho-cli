# project

Projects in the current account.

## `coho project create NAME [--no-use]`

`POST /api/v1/accounts/{account}/projects`. The account comes from the URL (the BFF
fills `organizationId` in); a body naming another account would be `ACCOUNT_MISMATCH`.
Bootstraps the trunk `v0.0.x` and four environments — `dev` (live, pointing at the
trunk), `qa`, `stage`, `prod` (snapshot, unset).

Records the project in the [local registry](../configuration.md#the-local-project-registry)
and, unless `--no-use`, makes it the current project with `v0.0.x` as the current ref.

Refusals: `PLAN_LIMIT` (project cap), `NOT_FOUND` (not a member of the account —
deliberately indistinguishable from a non-existent account).

## `coho project show [PROJECT]`

Id, name, trunk, and each environment's target. Default: the current project. Also
records the project in the registry.

## `coho project list`

⚠️ Local. The server has no listing endpoint yet (`coho-data` doc 04 §9), so this
shows the projects this profile has created, opened or registered for the current
account. `*` marks the current one.

## `coho project register ID [NAME]`

Fetches the project to check it exists and that you can see it, then remembers it
under `NAME` (default: its real name).

## `coho project forget NAME_OR_ID`

Drops it from the local registry. Nothing changes on the server.
