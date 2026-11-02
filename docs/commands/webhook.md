# webhook

Webhooks: the endpoints Coho calls when something happens in the current project
(coho-data doc 70), such as a promotion, a tag ready to deliver, a branch merged, entries
changed, or a token made. A static site rebuilt on promotion, a search index kept in step
with `main`, and a Slack channel told about a release all start here. Every request is
signed as [Standard Webhooks](https://www.standardwebhooks.com) signs one, with the
webhook's own secret, in the `webhook-signature` header.

Owners only, for every command here: a webhook sends project metadata to an address of the
owner's choosing, under a credential, as a token or a delivery key does. A project token is
never an owner, so it cannot manage them. A project has at most 25.

Every `ID` is a webhook's id, as `coho webhook list` shows it. Every `TIME` is ISO 8601,
`2026-11-02T14:00:00Z`, or a date, `2026-11-02`, which is midnight UTC; a time with no zone
is UTC.

## `coho webhook list`

`GET …/webhooks`: each webhook's id, host, events, and state, and its last day's
deliveries. The URL's path and query are left out; `show` has them.

```
ID                                    HOST                EVENTS                      STATE    LAST 24H
0192f1c3-7d1e-7a4b-9c2d-5e6f7a8b9c0d  build.example.com   environment.promoted, tag.*  enabled  12 ok, 0 failed
0192f1c9-0a2b-7c3d-8e4f-5a6b7c8d9e0f  hooks.slack.com     *                            failing since 2026-11-01T14:03:00Z  3 ok, 37 failed

2 of 25 webhooks.
```

`STATE` is `enabled`; `failing since` a time, while every attempt has failed since then; or
`disabled`, with the reason when it failed for five days and Coho turned it off.

## `coho webhook events`

`GET …/webhook-events`: the event types a webhook can subscribe to, then their groups,
each written `tag.*`. `*` is every event. A type not listed is refused
(`WEBHOOK_EVENT_UNKNOWN`), so no webhook waits for an event that never comes.

## `coho webhook create --url URL --event TYPE [--event …] [--ref PATTERN …] [--header 'Name: value' …] [--description TEXT] [--disabled]`

`POST …/webhooks`. Prints, **once**:

```
id  0192f1c3-7d1e-7a4b-9c2d-5e6f7a8b9c0d
url  https://build.example.com/hooks/coho
events  environment.promoted, tag.*
refs  prod
headers  Authorization
enabled  yes
Signing secret
whsec_…
```

The secret is stored sealed and never read back: lose it and `coho webhook rotate` makes
another. The warning goes to stderr, so `coho webhook create … > secret.txt` captures the
output alone; with `-o json` the whole `{secret, webhook}` response is printed.

- `--url` is HTTPS, on a public address: one that is, or resolves to, a private, loopback,
  or link-local address is refused (`WEBHOOK_URL_REFUSED`), and so is a user name or
  password in it (`WEBHOOK_URL_INVALID`).
- `--event` (repeatable) is a type, a group such as `tag.*`, or `*`.
- `--ref` (repeatable) sends only the events on refs that match, a name with `*` and `?` as
  wildcards. Leave it out for every ref.
- `--header` (repeatable, at most five) is sent with every request, for a receiver that
  checks a header rather than a signature. Its value is never shown again, and a header
  Coho sets itself, such as `content-type` or one starting `webhook-`, is refused
  (`WEBHOOK_HEADER_RESERVED`).
- `--disabled` makes it turned off; `coho webhook update ID --enable` turns it on.

## `coho webhook show ID`

`GET …/webhooks/{id}`: one webhook, with its full URL, its custom headers' names, its
state, its last delivery, and, while a rotation overlaps, when the previous secret stops
signing. Never its secret, and never a header's value.

## `coho webhook update ID [--url URL] [--event TYPE …] [--ref PATTERN …] [--all-refs] [--header 'Name: value' …] [--clear-headers] [--description TEXT] [--enable | --disable]`

`PATCH …/webhooks/{id}`: changes what you pass, leaves the rest, and prints the webhook.

- `--event` and `--ref` replace the whole list; `--all-refs` sends every ref's events again.
- `--header` replaces every custom header, since their values cannot be read back to merge
  with; `--clear-headers` sends none.
- `--description ''` clears the description.
- `--enable` also clears the run of failures that turned it off. What failed while it was
  off is in its log, to send again with `redeliver`.

## `coho webhook delete ID`

`DELETE …/webhooks/{id}`. Asks first, unless `--yes`. Its deliveries and their log go
with it.

## `coho webhook rotate ID`

`POST …/webhooks/{id}/rotate-secret`: a new signing secret, printed once, and when the
previous one stops signing, 24 hours on. Until then every request carries two signatures,
one for each secret, so a receiver can be given the new one at its own pace. Rotating again
before then stops the previous one at once, which is how a leaked secret is answered:
rotate twice.

## `coho webhook test ID`

`POST …/webhooks/{id}/test`: a `ping` to this webhook alone. It is queued, not sent while
you wait: the sender sends it within seconds, and `coho webhook delivery ID DELIVERY_ID`
then shows how it went. A disabled webhook is refused (`WEBHOOK_INVALID`).

## `coho webhook deliveries ID [--state S] [--type T] [--since TIME] [--before TIME] [--limit N]`

`GET …/webhooks/{id}/deliveries`: the log, newest first, 50 at a time unless `--limit`
(at most 200) says otherwise.

```
DELIVERY                              CREATED               TYPE                  STATE      RESULT
0192f2a0-1b2c-7d3e-8f4a-5b6c7d8e9f0a  2026-11-02T14:03:07Z  environment.promoted  failed     timeout after 9 attempts
0192f29e-4c5d-7e6f-8a7b-9c0d1e2f3a4b  2026-11-02T13:58:41Z  tag.ready             succeeded  200
```

- `--state` is `held` (a promotion's, until its release can be read), `pending`, `running`,
  `succeeded`, or `failed`.
- `--type` is one event type, such as `tag.ready`.
- `--since` and `--before` bound when each was made. For the next page, pass the last
  `CREATED` shown as `--before`.

`RESULT` is the last attempt's status, or the kind of failure when there was no answer:
`dns`, `refused_address`, `connect`, `tls`, `timeout`, `redirect`, `http`, or `internal`.
Kept 30 days when it failed and 7 when it succeeded.

## `coho webhook delivery ID DELIVERY_ID`

`GET …/webhooks/{id}/deliveries/{deliveryId}`: the delivery, then every attempt it made:
when it started, the receiver's status, the kind of failure, how long it took, and the
first words of the response, or what went wrong when there was none.

```
#  STARTED               STATUS  ERROR    TOOK      RESPONSE
1  2026-11-02T14:03:07Z  503     http     212 ms    upstream connect error
2  2026-11-02T14:03:38Z  -       timeout  15000 ms  The receiver did not answer within 15 seconds
```

With `-o json`, the whole delivery: the body exactly as it was signed, and each attempt's
request headers (the signature and custom header values masked), response headers, and
first 2 KB of response.

## `coho webhook redeliver ID DELIVERY_ID`

`POST …/webhooks/{id}/deliveries/{deliveryId}/redeliver`: sends a finished delivery once
more, with the same event id (the `webhook-id` header), so a receiver that handled it
already can drop it. One still being sent is refused (`BAD_REQUEST`).

## `coho webhook redeliver ID --failed-since TIME`

`POST …/webhooks/{id}/redeliver?since=`: sends every delivery that failed since `TIME`
once more, after your receiver's outage, and says how many.
