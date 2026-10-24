# project

Projects in the current account.

## `coho project create NAME [--no-use]`

`POST /api/v1/accounts/{account}/projects`. The account comes from the URL (the BFF
fills `organizationId` in); a body naming another account would be `ACCOUNT_MISMATCH`.
Bootstraps the trunk `v0.0.x` and four environments — `dev` (live, pointing at the
trunk), `qa`, `stage`, `prod` (snapshot, unset).

Records the project in the [local registry](../configuration.md#the-local-project-registry)
and, unless `--no-use`, makes it the current project with `v0.0.x` as the current ref.

Refusals: `PLAN_LIMIT` (project cap), `PROJECT_NAME_TAKEN` (another project in the
account has that name, ignoring case and surrounding spaces — even one you cannot see),
`NOT_FOUND` (not a member of the account — deliberately indistinguishable from a
non-existent account).

## `coho project rename NAME`

`PATCH /api/v1/accounts/{account}/projects/{project}`. An account admin's. Renames the
current project, or the one `--project` names.

**Only the name changes.** The project's id, its delivery URLs, its delivery keys and
its project tokens are all untouched, so nothing you have deployed, shared or scripted
has to be updated. An archived project can be renamed too: archiving makes its *content*
read-only, and the name is the organization's label for it.

The [local registry](../configuration.md#the-local-project-registry) is updated: the old
name is dropped and the new one recorded. Dropping it matters, because the server frees
the old name at once — another project in the account may take it, and an alias left
pointing here would then resolve to the wrong project. Your own aliases from
`coho project register` are left alone.

Refusals: `PROJECT_NAME_TAKEN` (another project in the account has that name, ignoring
case and surrounding spaces), `BAD_REQUEST` (a blank name), `FORBIDDEN` (a member of the
account who is not an admin), `TOKEN_NOT_ALLOWED` (a project token), `NOT_FOUND` (no
access to the project — the same answer as for one that does not exist).

## `coho project show [PROJECT]`

Id, name, trunk, and each environment's target. Default: the current project. Also
records the project in the registry.

## `coho project list`

`GET /api/v1/accounts/{account}/projects`: every project in the current account you
can open, and your role on each — all of them, as `owner`, for an account admin; the
ones granted to you otherwise. `*` marks the current one. A project the local
registry remembers but the server no longer lists for you (deleted, or your access
removed) is shown as `local only`.

## `coho project usage [PROJECT]`

What the project used, metered hourly in UTC (coho-data doc 41): `GET
…/projects/{project}/usage`. Default: the current project. Anyone who can read the
project may, project tokens included, so a pipeline can watch its own.

```
coho project usage                         # the last day, hour by hour
coho project usage site --grain day        # the last 30 days, day by day
coho project usage --from 2026-10-01 --to 2026-10-08 --grain day
coho project usage --meter delivery.requests --meter delivery.bytes
coho project usage --periods               # and a line per hour
coho -o json project usage                 # the report exactly as the server sent it
```

The table has four parts. **Delivery**: requests, 304s, refusals, bytes sent and
billable, the peak per minute, and a line per delivery key with its requests per
distinct URL per period. A client that caches asks for each URL about once per tag, and
once per `max-age` for an environment; tens or hundreds a URL is one fetching the same
answer again, and sending `If-None-Match` turns a repeat into a `304`. **Management**:
requests by people and by project tokens, split by class, versions written and how many
changed nothing, and preview reads. **Content and history**, and **Assets**, whose
traffic comes from the CDN's logs minutes after the request.

`--from` and `--to` take ISO 8601; a bare date is midnight UTC. `--from` is rounded down
and `--to` up to whole periods, and `--to` is exclusive. Hourly rows are kept 90 days,
so ask for `--grain day` further back; a range the stored data cannot answer is
`USAGE_QUERY_INVALID`. `--meter` shows just those meters, each with its series. The
totals are the portal's: a flow sums, a peak takes its largest period, a stock its
latest value.

`coho account usage` is the account's, every project summed, for its admins.

## `coho project register ID [NAME]`

Fetches the project to check it exists and that you can see it, then remembers it
under `NAME` (default: its real name).

## `coho project forget NAME_OR_ID`

Drops it from the local registry. Nothing changes on the server.
