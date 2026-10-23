# tier

The promotion pipeline: an ordered list of tiers, each guarding its environments with
`promote:<tier id>`. Editing the pipeline is grant assignment in different clothes, so
it is `workflow:write` — **owner only**.

## `coho tier list`

Order, id, `resolves`, the permission string, the environments in it.

A tier's `ord` is its position: 0 to n-1, with no gaps. It decides where a tier is
listed and which earlier tiers the skipped-tier warning counts, and it never gates a
promotion.

## `coho tier create ID --resolves live|snapshot --ord N`

`POST …/tiers`. `resolves` is immutable after creation: flipping it on a populated tier
would leave every environment pointing at the wrong kind of ref.

`--ord` is where to insert it. A taken position moves that tier and every one after it
along by one, so `coho tier create uat --resolves snapshot --ord 3` on the seeded
pipeline puts `uat` before `prod`, and `prod` moves to 4. One past the end, or anything
larger, is the end. Prints the position the tier got. Refusals: `TIER_ID_TAKEN`, and
`PLAN_LIMIT` on a plan whose pipeline is fixed (Free and Site).

## `coho tier move ID --ord N`

`PATCH …/tiers/{id}`. Moves the tier, and the tiers it passes shift by one toward the
place it left. Only the position can change. `TIER_NOT_FOUND` if there is no such tier.

## `coho tier delete ID`

Only an empty tier: `TIER_NOT_EMPTY` names the environments still holding it open. The
tiers after it move up one.
