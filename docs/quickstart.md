# Quickstart

Ten minutes from nothing to a promoted release. Every command here has a page in the
[command reference](commands/index.md).

## 1. Point at your BFF and sign in

```bash
coho configure --profile staging --url https://staging.coho.example \
    --oidc-domain https://acme.auth.us-east-1.amazoncognito.com --client-id 1h57kf5cpq17m0eml12EXAMPLE
coho login
```

`login` opens the hosted sign-in in your browser and stores the tokens in your OS
keyring. If your deployment has no app client for the CLI yet, store a token you
obtained elsewhere instead: `coho login --token "$TOKEN"`. See
[authentication](authentication.md).

```bash
coho whoami
```

```
user     0192a3…
name     Ada Lovelace
email    ada@acme.example
profile  staging

ACCOUNT  ID       ROLE   ACTOR
Acme     0192b4…  admin  0192c5…
```

## 2. Set the account and create a project

```bash
coho use acme
coho project create "Marketing site"
```

Creating a project bootstraps the trunk `v0.0.x` and four environments: `dev` (live,
pointing at the trunk) and `qa`, `stage`, `prod` (snapshot tiers, unset). `project
create` also makes it your current project and `v0.0.x` your current ref, so the
next commands need no flags.

```bash
coho status
```

## 3. Define a content type

`blogPost.json`:

```json
{
  "_name": "Blog post",
  "fields": [
    { "id": "title",       "type": "text",     "required": true, "localized": true },
    { "id": "body",        "type": "longText", "localized": true },
    { "id": "publishedAt", "type": "datetime" },
    { "id": "rank",        "type": "integer" },
    { "id": "author",      "type": "reference", "of": ["teamMember"] }
  ]
}
```

```bash
coho type put blogPost --file blogPost.json
coho type list
```

Field ids start with a letter; `_` is reserved. See [content model](content-model.md).

## 4. Write an entry

```bash
coho entry create -t blogPost -s hello-world \
    --set title.en-US="Hello, world" --set body.en-US="First post." --set rank=1
```

```bash
coho entry list --type blogPost
coho entry get 0192d6…              # prints the fields and the ETag
```

Edit and write back — the CLI does the read-modify-write with `If-Match` for you:

```bash
coho entry put 0192d6… --set title.en-US="Hello again"
```

Or replace the fields wholesale from a file, which needs the ETag from your last read
(or `--force`):

```bash
coho entry get 0192d6… --fields > post.json
$EDITOR post.json
coho entry put 0192d6… --file post.json --if-match '"0192e7…"'
```

## 5. Branch, review, merge

```bash
coho branch create feature/pricing --use     # from the current ref; switches context to it
coho entry put 0192d6… --set title.en-US="New pricing"
coho diff v0.0.x                              # what merging this branch into the trunk would do
```

```
from       v0.0.x
to         feature/pricing
mode       diverged
base       v0.0.x@42
added      0
modified   1
deleted    0
conflicts  0
merge token  eyJ…
```

```bash
coho merge --into v0.0.x -m "New pricing copy" --reviewed
```

`--reviewed` runs the diff and passes its `mergeToken` as `expectedToken`, so the
merge is refused with `MERGE_REFS_MOVED` if anything changed since you looked. When
there are conflicts, the merge is refused whole and the conflicts are printed; see
[merge](commands/merge.md) for how to resolve them.

## 6. Cut a release and promote it

```bash
coho use acme "Marketing site" v0.0.x
coho tag create v1.0.0 -m "First release"     # immutable (branch, seq) coordinate
coho promote qa v1.0.0                        # waits while the snapshot builds
coho promote stage v1.0.0
coho promote prod v1.0.0 -m "Go live"
coho env list
```

Something wrong? Roll back, conditionally on nobody having fixed it forward:

```bash
coho rollback prod
```

## 7. Let a website read it

```bash
coho key create --label site-prod --ref prod
```

The key is printed once. Only its hash is stored; lose it and you issue another.

## 8. Bring a colleague in

```bash
coho invite create jane@acme.example --role member     # prints the link, once
coho role grant <actor-id> author                       # project role; see `coho role ladder`
```

## Scripts

Every command takes `--output json` and prints exactly what the contract describes:

```bash
coho -o json entry list --all | jq '.entries[] | .slug'
```

See [CI usage](ci.md).
