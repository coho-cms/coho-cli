# account

Accounts you belong to. Membership comes from `/api/v1/me`, read fresh each call.

| Command | Needs | What it does |
|---|---|---|
| `account list` | login | accounts with your role and actor id |
| `account show [ACCOUNT]` | login | one account; adds plan and limits when you are its admin |
| `account rename NAME` | admin | `PATCH /api/v1/accounts/{id}` |
| `account entitlements` | admin | plan, plan status, `maxProjects`, `maxLiveEnvironments`, `maxMembers`; an absent limit is **unlimited** |
| `account events [--limit N]` | admin | the audit trail, newest first, up to 200 |
| `account plans [--include-retired]` | login | the plan catalogue |

Limits are enforced at the write path in the tiers; a refused write answers
`PLAN_LIMIT` with `limit` and `current`. `entitlements` is for showing what a plan
allows before someone builds up to the cap.

Audit event actions include `member.joined`, `member.role_changed`, `member.removed`,
`member.left`, `invitation.created`, `invitation.revoked`, `account.renamed`,
`account.plan_changed`, `user.renamed`, `login.attached`, `login.detached`,
`actor.bound`. `BY` is `operator` for actions taken by the platform operator, and
`(erased user)` when the actor has since been erased.
