---
name: coho
description: Work with Coho, the branch-native headless CMS, through its `coho` command line. Use when the user wants to read or change Coho content (types, entries, assets), branch, diff, merge, tag, or promote a release, manage projects, roles, delivery keys, project tokens or webhooks, or asks what they are able to do in Coho.
allowed-tools: Bash(coho status *) Bash(coho whoami *) Bash(coho --help *) Bash(coho --version *) Bash(coho role ladder *) Bash(coho account list *) Bash(coho account show *) Bash(coho project list *) Bash(coho project show *) Bash(coho ref list *) Bash(coho ref show *) Bash(coho ref describe *) Bash(coho branch list *) Bash(coho tag list *) Bash(coho type list *) Bash(coho type get *) Bash(coho trait list *) Bash(coho trait get *) Bash(coho entry list *) Bash(coho entry get *) Bash(coho entry history *) Bash(coho entry references *) Bash(coho asset list *) Bash(coho asset get *) Bash(coho env list *) Bash(coho env show *) Bash(coho env history *) Bash(coho diff *)
---

# Working with Coho through `coho`

`coho` manages Coho: accounts, projects, content types and entries, and the branches,
tags and environments that carry content to a website. It works like `git` (a sticky
context, `branch`, `diff`, `merge`, `tag`) crossed with `aws` (profiles,
`<noun> <verb> [--flags]`, JSON for programs).

If `coho` is not installed, tell the user: `uv tool install coho-cli` (or
`pipx install coho-cli`).

## 0. Read `COHO.md` if the repository has one

`coho init --agents` writes `COHO.md` from the live project: its account and project ids,
every content type with its fields (required, localized, choices, references), the
locales its entries use, its refs and environments, and the rules for this project. Read
it before any other step, and use its ids, slugs, field ids and locales rather than
guessing. If the content model looks different from what it says, suggest the user run
`coho init --agents` to regenerate it; do not edit it by hand.

A repository that works with a Coho project but has no `COHO.md` can have one:
suggest `coho init --agents` to the user.

## 1. Start with `coho status`

Run it before anything else, and again after changing context. It says who you are acting
as and what you may do **here**, so you can plan without trying and failing:

```bash
coho status
```

Its JSON (the default when your output is captured) has:

- `credential`: `null` means nobody is signed in (see §2). `kind` is `person` or
  `project_token`; `source` says where it came from.
- `account`, `project`, `ref`: the context every command uses unless given flags.
- `accountRole`: `admin` or `member`. A project token has none.
- `projectRole`: `viewer` < `author` < `maintainer` < `release_manager` < `owner`.
- `permissions`: what that role may do in this project. `["*"]` is everything (owner).
  `[]` means nothing here: a project token works only in its own project. `null` means
  there is no project in the context yet.

What each permission allows:

| Permission | Lets you |
|---|---|
| `content:read` | read types, entries, assets, refs, diffs |
| `content:write` | create, change and delete types, traits, entries, assets on a branch |
| `branch:create` | create feature branches |
| `promote:preview` | point a personal `preview` environment at a ref |
| `merge` | merge one ref into another |
| `release:tag` | cut tags |
| `promote:dev`, `promote:qa`, `promote:stage`, `promote:prod` | point that tier's environments at a tag or ref, and roll them back |
| `branch:create_version` | create a version branch such as `v1.1.x` |
| owner only (`*`) | grant roles, delivery keys, project tokens, webhooks, workflow settings |

Do not attempt what the permissions rule out: say what is missing and who can grant it
(a project `owner`, or an account `admin`, with `coho role grant`).

## 2. Signing in is the user's job

You cannot finish a sign-in: it needs a browser and a password. If `credential` is `null`,
or a command fails with exit code 3 (`NOT_LOGGED_IN`, `UNAUTHENTICATED`,
`AUTH_NO_TERMINAL`), ask the user to run this themselves, in their own terminal:

```bash
coho login
```

On a machine with no browser it prints a URL to open anywhere and asks for a code.
⚠️ **Never ask the user for that code, a password, or a token**, and never put one in a
command you run. The sign-in page warns people about exactly that request.

For automation, the credential is a **project token** in `COHO_TOKEN`: one role in one
project, made by an owner with `coho token create`. If one is set, `status` shows its
label, role and expiry.

## 3. Output

- Your captured output is JSON by default (stdout is not a terminal), the server's
  response as documented. Parse it rather than scraping text. Pass `-o table` only to
  show the user a table.
- Errors go to stderr as `error CODE: detail`. Branch on the code, never on wording.
- Exit codes: `0` ok · `1` refused or failed · `2` usage (bad arguments, no context) ·
  `3` not signed in · `4` a precondition moved, so re-read and retry · `5` not found.
- `coho <command> --help` lists the flags, and its last line links the full page in the
  docs.

## 4. Context

`account`, `project` and `ref` are saved per profile with `coho use`, and every command
uses them. **Do not change the user's saved context to do a one-off task.** Pass flags
instead, which apply to that command only:

```bash
coho entry list --project 0192c5… --ref feature/pricing
```

Use `coho use <account> [<project> [<ref>]]` when the user asks to switch, and say that
you did. `coho ref switch NAME` and `coho branch create NAME` also move the saved ref.

Names work for accounts and projects. A project token cannot look names up, so with one,
use the ids that `coho status` prints.

## 5. Common tasks

Read content:

```bash
coho type list
coho type get blogPost
coho entry list --type blogPost
coho entry get ENTRY_ID
coho entry history ENTRY_ID
```

Change an entry. `--set` does the read-modify-write, with `If-Match`, for you:

```bash
coho entry put ENTRY_ID --set title.en-US="New title"
coho entry create -t blogPost -s hello-world --set title.en-US="Hello"
```

Localized fields are `field.locale`, such as `title.en-US`. A `VERSION_CONFLICT` (exit 4)
means someone else wrote first: read it again, reapply, and retry.

Change a content type: write the definition to a file, then
`coho type put blogPost --file blogPost.json`. A change that would destroy data is
refused with `DESTRUCTIVE_SCHEMA_CHANGE`. Show the user the errors; do not pass
`--confirm-destructive` without their explicit say-so.

Work on a branch, and show what merging it would do:

```bash
coho branch create feature/pricing      # from the current ref, and switches to it
coho entry put ENTRY_ID --set …
coho diff v0.0.x                        # what merging into the trunk would do
```

## 6. Releasing is the user's job

**Never run `coho merge`, `coho tag create`, `coho promote` or `coho rollback`**, even
when the role allows them. They decide what is released and what a live website serves.
When the work is ready, give the user the commands to run themselves, for example:

```bash
coho merge --into v0.0.x -m "Pricing copy" --reviewed   # merges only what the diff showed
coho tag create v1.0.0 -m "First release"
coho promote qa v1.0.0
```

If the user asks you to run one of them in so many words, say exactly what you will run
and wait for a yes. A refused merge with conflicts lists them: show them to the user
rather than resolving them yourself.

## 7. Ask the user before you…

These change who can do what, or cannot be undone. Say exactly what you will run and wait
for a yes:

- any `delete`, `revoke`, `remove`, `unset`, or `--yes`, which skips a confirmation
- `coho role grant` and `revoke`, and `coho member role` and `remove`
- `coho key create`, `coho token create`, `coho webhook create` and `rotate`: each prints
  a secret **once**. Tell the user to store it, and do not repeat it in your reply.
- `--force`, `--confirm-destructive`, or anything that overwrites someone else's change

Reading, listing, `status`, `diff`, and changing content on a feature branch the user
asked you to work on need no extra confirmation.

## 8. Where to look

- `coho <noun> --help`: the flags, and a link to the command's page.
- Docs: https://github.com/coho-cms/coho-cli/blob/HEAD/docs/index.md, including
  [concepts](https://github.com/coho-cms/coho-cli/blob/HEAD/docs/concepts.md) (refs,
  branches, tags, environments, tiers, roles),
  [content model](https://github.com/coho-cms/coho-cli/blob/HEAD/docs/content-model.md)
  (field types, locales, references), and
  [errors](https://github.com/coho-cms/coho-cli/blob/HEAD/docs/errors.md) (every code).
