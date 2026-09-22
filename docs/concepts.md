# Concepts

What the nouns mean, and who may touch them. The design notes in `coho-data/docs`
are the source; this is the working summary.

## Account, project, actor

An **account** is the customer. A person can belong to several, with an account-level
role of `admin` or `member`. A **project** belongs to one account and holds one content
graph: types, entries, refs.

Inside a project you act as an **actor** — an id minted for you in that account the
first time you do anything there. Project roles are granted to actors. The CLI never
sees the credential behind an actor; the BFF sets it from the account in the URL.

## Refs: one namespace

Branches, tags and environments share one namespace in a project. `coho ref list`
shows all of them; `kind` says which.

| Kind | What it is | Moves? | Writable? |
|---|---|---|---|
| `version_branch` | A line of releases. The trunk is `v0.0.x`. Only version branches can be tagged. | tip moves with writes | yes |
| `feature_branch` | Work in progress, branched from a version branch or a tag. Merged back. | tip moves with writes | yes |
| `tag` | An immutable `(branch, seq)` coordinate. Undeletable. | never | no |
| `environment` | A name that points at a tag (snapshot tier) or a branch tip (live tier). | on every promotion | no |

Branch names contain slashes (`feature/pricing`); the CLI encodes them.

**Sequence, not time.** A project's history is ordered by `seq`, a commit id allocated
under a lock. `--at` on `branch create` and `tag create` takes a sequence, never a
timestamp, because a branch point is permanent and a tag is a release artifact.

## Branch, diff, merge

Creating a branch is O(1) and copies nothing. A branch sees its parent's history up to
the branch point, then its own edits.

`coho diff FROM TO` compares `TO` (the branch under review) against `FROM` (where it
would land). The default is three-dot (`diverged`): changes since the two diverged. It
also previews the merge — `conflicts` and a `mergeToken`. `--absolute` is two-dot and
reports every change the target made that the branch lacks, as though the branch
reverted them; it is not the default for that reason.

`coho merge SOURCE --into TARGET` is a three-way merge that lands whole or is refused
whole. Conflicts come back on the error with `nodeId` and key-based `paths`; you answer
each with a **resolution** naming `source`, `target` or a literal `value`. Naming a side
rather than repeating its content is what lets a resolution express *absence*. See
[merge](commands/merge.md).

## Tag and promote: two decisions, two people

`tag create` stamps a coordinate on a version branch. It does not merge and does not
validate — a version branch tip is always valid, so there is nothing left to check.
Requires `release:tag`.

`promote ENV TARGET` repoints an environment. Requires `promote:<tier>` of that
environment's tier — a different permission from tagging, on purpose: producing the
artifact and deploying it are different decisions.

A **snapshot** environment (`qa`, `stage`, `prod` by default) points at tags; the
first promotion of a tag may answer `SNAPSHOT_NOT_READY` while the artifact builds,
and the CLI waits. A **live** environment (`dev`) points at a branch tip and serves
whatever is there now.

Promoting past a tier (`dev` → `prod`) is allowed and returns a `SKIPPED_TIER`
warning, because a hard gate would make the hotfix flow illegal. The permission ladder
is the gate.

**There is no rollback endpoint.** `coho rollback ENV` reads the environment's history
and issues the same repoint at the previous target, with `expectedTarget` set to the
current one, so it fails with `ENVIRONMENT_MOVED` if someone already fixed it forward.

## Tiers

The pipeline is a list of tiers, each `live` or `snapshot` (immutable once created),
each guarding its environments with `promote:<tier id>`. The seeded four are
single-environment tiers. `coho tier create qa2 --resolves snapshot --ord 15` needs no
new grant: whoever holds `promote:qa2` may promote there. Owner only.

## Roles and permissions

Account roles (`admin`, `member`) govern membership and invitations. Project roles
govern content:

| Role | Permissions |
|---|---|
| `viewer` | `content:read` |
| `author` | + `content:write`, `branch:create` |
| `maintainer` | + `merge`, `release:tag`, `promote:dev`, `promote:qa` |
| `release_manager` | + `promote:stage`, `promote:prod`, `branch:create_version` |
| `owner` | all: `role:grant`, `delivery:keys`, `workflow:write` |

An account admin holds implied `owner` on every project in the account, so a project
whose grants went wrong is always repairable. `coho role list` shows actor ids, never
names — the content tier is not a directory; join with `coho member list`.

A project you have no role in is `404`, not `403`: telling you it exists would be a
disclosure. Beyond read access, refusals are `403 FORBIDDEN` with the missing
`permission` named.

## Delivery keys and public refs

A website reads published content from the delivery tier with a **delivery key**
(`coho key create`), optionally limited to named refs and to an expiry. Only the hash is
stored; the key is shown once. Revocation takes effect within a few seconds.

`coho key public prod` opens named **environments** to keyless reads. The tag behind
`prod` stays key-required when addressed directly.

## Export and preview

`coho export REF` writes a tag's prebuilt image (usually via a presigned URL) or
computes a branch's at its current tip, reporting the sequence it was resolved at.
Nothing exported is importable yet, and the manifest says so.

`coho preview entries` reads a ref through the **delivery contract** — the same shape a
website will get — before it is published. It goes through the BFF because the live
implementation is private.
