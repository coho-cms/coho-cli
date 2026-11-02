# Errors and exit codes

## Branch on `code`

Every refusal from Coho is a problem document with a stable `code`. Domain failures
are all `400` with a distinct code; only failures where an HTTP mechanism depends on
the status keep a specific one (401, 403, 404, 412, 428). The same code can arrive with
different statuses from different tiers (`PLAN_LIMIT` is 409 from the auth tier and
400 from authoring). **Never branch on status.**

The CLI prints `error CODE: detail` on stderr, plus the problem's context fields
(`permission`, `ref`, `slug`, `errors[]`, `conflicts[]`, `invalidEntries[]`) when
present. With `--output json`, a `MERGE_CONFLICT` or a `TAG_CONTENT_INVALID` prints the
whole problem document on stdout so a script can read the conflicts or the entries.

## Exit codes

| Code | Meaning | Examples |
|---|---|---|
| 0 | success | |
| 1 | a refusal, or an unexpected failure | `VALIDATION_FAILED`, `FORBIDDEN`, `PLAN_LIMIT`, `TRANSPORT` |
| 2 | usage: bad arguments, missing context, unknown profile | "no ref in context" |
| 3 | not authenticated | `NOT_LOGGED_IN`, `UNAUTHENTICATED`, a failed login |
| 4 | a precondition failed — retry after re-reading | `VERSION_CONFLICT`, `PRECONDITION_REQUIRED`, `MERGE_CONFLICT`, `ENVIRONMENT_MOVED` |
| 5 | not found | `NOT_FOUND`, `REF_NOT_FOUND`, `ENTRY_NOT_FOUND` |
| 130 | interrupted | Ctrl-C |

## Catalogue

### Authoring and BFF (RFC 9457 problems)

| `code` | Status | Context | Meaning |
|---|---|---|---|
| `UNAUTHENTICATED` | 401 | | no or bad credential |
| `FORBIDDEN` | 403 | `permission` | the actor lacks the named permission |
| `USER_SUSPENDED`, `ACCOUNT_SUSPENDED`, `ACCOUNT_CLOSED` | 403 | | no grant fixes these |
| `NOT_FOUND` | 404 | | also: an account you are not in, a project you have no role in |
| `REF_NOT_FOUND` | 404 | `ref` | |
| `ROUTE_NOT_FOUND` | 404 | | |
| `VERSION_CONFLICT` | 412 | `expectedVersion`, `currentVersion` | `If-Match` is stale |
| `PRECONDITION_REQUIRED` | 428 | `header` | an update without `If-Match` |
| `BAD_REQUEST`, `MALFORMED_BODY` | 400 | | |
| `ACCOUNT_MISMATCH` | 400 | | body names a different account than the URL |
| `VALIDATION_FAILED` | 400 | `errors[]` | document does not match its type |
| `SCHEMA_INVALID` | 400 | | bad type definition |
| `DESTRUCTIVE_SCHEMA_CHANGE` | 400 | `errors[]` | needs `--confirm-destructive` |
| `SLUG_CONFLICT` | 400 | `slug`, `ref` | |
| `INTERNAL_NAME_CONFLICT` | 400 | `ref` | |
| `TYPE_IN_USE` | 400 | `slug`, `entryCount` | delete refused |
| `SINGLETON_BLOCKED` | 400 | | a type made a singleton while its ref holds more than one of its entries, a type that extends it, or its entry under another slug |
| `PIN_LIMIT` | 400 | | `pin add` past 20 pins in the project; unpin one first |
| `BRANCH_NOT_WRITABLE` | 400 | `ref` | writing to a tag or environment |
| `REF_NAME_TAKEN` | 400 | `ref` | |
| `BRANCH_TOO_DEEP` | 400 | `depth`, `maxDepth` | |
| `CANNOT_BRANCH_FROM` | 400 | `ref` | |
| `INVALID_BRANCH_POINT`, `INVALID_TAG_POINT` | 400 | | `--at` out of range |
| `AT_OUT_OF_RANGE` | 400 | `at`, `highWaterMark`; `ref` for a tag | a read's `--at` below zero, beyond the project's high-water mark, or past the tag |
| `TAG_CONTENT_INVALID` | 400 | `entryCount`, `invalidEntries[]` | `tag create --validate` found invalid entries; nothing was tagged |
| `MERGE_CONFLICT` | 400 | `conflicts[]` | needs resolutions |
| `MERGE_RESOLUTION_REJECTED` | 400 | | a resolution does not apply |
| `MERGE_REFS_MOVED` | 400 | | the refs changed since the diff you reviewed |
| `CANNOT_MERGE` | 400 | | |
| `TIER_NOT_FOUND`, `TIER_ID_TAKEN`, `TIER_NOT_EMPTY` | 400 | | |
| `NOT_AN_ENVIRONMENT`, `INVALID_PROMOTION_TARGET` | 400 | | |
| `ENVIRONMENT_MOVED` | 400 | | `--expected` did not match |
| `LIVE_ENVIRONMENT_LIMIT` | 400 | | |
| `SNAPSHOT_NOT_READY` | 400 | `state` | the CLI waits unless `--no-wait` |
| `PLAN_LIMIT` | 400 / 409 | `limit`, `current` | the account's plan |
| `ASSET_TOO_LARGE` | 400 | `limit`, `current` | over the per-file limit, 1 GiB; `asset upload` refuses it first |
| `ASSET_TYPE_NOT_ALLOWED` | 400 | | the bytes are not an image, PDF, audio or video, whatever the name |
| `ASSET_UPLOAD_INCOMPLETE` | 400 | | completed before the bytes arrived, or other bytes |
| `ASSET_UPLOAD_EXPIRED` | 400 | | not completed within the hour |
| `ASSETS_UNAVAILABLE` | 503 | | the deployment has no asset store |
| `WEBHOOK_URL_INVALID` | 400 | | a webhook's URL is not HTTPS, or has a user name or password in it |
| `WEBHOOK_URL_REFUSED` | 400 | | a webhook's URL is, or resolves to, a private, loopback, or link-local address; the detail names it |
| `WEBHOOK_EVENT_UNKNOWN` | 400 | | not an event a webhook can subscribe to; `coho webhook events` lists them |
| `WEBHOOK_HEADER_RESERVED` | 400 | | a custom header Coho sets itself, such as `content-type` or one starting `webhook-` |
| `WEBHOOK_LIMIT_REACHED` | 400 | | the project has 25 webhooks; delete one first |
| `WEBHOOK_INVALID` | 400 | | anything else about a webhook the server will not keep, or a test sent to a disabled one; the detail says which |
| `WEBHOOKS_UNCONFIGURED` | 503 | | the deployment has no key to seal webhook secrets with, so it keeps no webhooks |
| `PROJECT_ARCHIVED` | 400 | | a change to an archived project; reading, such as a webhook's log, still works |
| `UPLOAD_REJECTED` | — | `storageCode` | object storage refused the bytes on its presigned URL; not from the API |
| `UPSTREAM_UNAVAILABLE` | 502 | | the BFF could not reach a tier |
| `INTERNAL` | 500 | | opaque by design |

### Auth tier (`{code, detail}`, relayed untouched)

| `code` | Status | Meaning |
|---|---|---|
| `INSUFFICIENT_SCOPE` | 403 | the token lacks `coho-auth/accounts` (or `self`) |
| `ACCOUNT_ADMIN_REQUIRED` | 403 | member, not admin |
| `EMAIL_NOT_EDITABLE` | 403 | |
| `INVALID` | 400 | bad role, blank name, non-UUID id … |
| `LAST_ADMIN` | 409 | would leave members with no admin |
| `LAST_LOGIN` | 409 | detaching your only identity |
| `ALREADY_REGISTERED` | 409 | |
| `ACCOUNT_CLOSED` | 409 | |
| `INVITATION_USED`, `INVITATION_ACCEPTED`, `INVITATION_REVOKED`, `INVITATION_EXPIRED` | 409 | two codes for "used", depending on the verb |
| `PLAN_LIMIT` | 409 | member cap |

### The SDK's own

| `code` | Meaning |
|---|---|
| `NOT_LOGGED_IN` | no token for the profile |
| `AUTH` | the login flow failed before any Coho request |
| `TRANSPORT` | could not reach the server |
| `HTTP_<status>` | a non-problem response (a proxy's HTML page) |
| `NO_PREVIOUS_TARGET` | `rollback` found nothing to go back to |

In Python these are `CohoError` subclasses; see the
[library's error reference](https://github.com/coho-cms/coho-management-sdk-python/blob/HEAD/docs/errors.md).
