# tier

The promotion pipeline: an ordered list of tiers, each guarding its environments with
`promote:<tier id>`. Editing the pipeline is grant assignment in different clothes, so
it is `workflow:write` — **owner only**.

## `coho tier list`

Order, id, `resolves`, the permission string, the environments in it.

## `coho tier create ID --resolves live|snapshot --ord N`

`POST …/tiers`. `resolves` is immutable after creation: flipping it on a populated tier
would leave every environment pointing at the wrong kind of ref. `ord` is display
order and does not gate promotion. Refusals: `TIER_ID_TAKEN`, `TIER_ORDER_TAKEN`.

## `coho tier delete ID`

Only an empty tier: `TIER_NOT_EMPTY` names the environments still holding it open.
