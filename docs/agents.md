# Coding agents

`coho` is built to be run by an AI coding agent, such as Claude Code, as well as by a
person. What a cold agent lacks is the project: its content types, its locales, its
refs, and what it may do there. Three things give it that.

## 1. `COHO.md`, from the live project

```bash
coho init --agents
```

Writes `COHO.md` into the repository: the project's ids, every content type with its
fields, the locales in use, the refs and environments, and the rules for changing
content safely. `AGENTS.md` and `CLAUDE.md` get a short block pointing at it. Commit
them, and run it again after the content model changes: generated from the project, the
file never drifts from it, which every hand-written `CLAUDE.md` about a content model
does. `--check` in CI says when it is out of date. See [`coho init`](commands/init.md).

## 2. `coho status`, for what it may do

```bash
coho -o json status
```

Says which credential is in use (a person signed in with `coho login`, or a project token
in `COHO_TOKEN`), its account role, its project role, and that role's permissions, so the
agent can tell what it may do before it tries. See [`coho status`](commands/context.md#coho-status).

Give an agent a **project token** with the least role it needs (`author` drafts content
on branches; it cannot merge or release), rather than a person's login:

```bash
coho token create --role author --label "Claude drafting" --expires 30
```

## 3. The Claude Code plugin

This repository is a Claude Code plugin whose skill teaches Claude to read `COHO.md`,
start from `coho status`, keep to what the role allows, leave signing in and releasing to
a person, and ask before anything destructive:

```
/plugin marketplace add coho-cms/coho-cli
/plugin install coho@coho-cms
```

It pre-approves only commands that read. See [install](install.md#claude-code).

## What `coho` does for a program

- **JSON when it is not a terminal.** Output is JSON whenever stdout is captured, the
  server's response as the contracts describe it. `-o table` or `-o json` chooses
  explicitly. Errors go to stderr as `error CODE: detail`, with an
  [exit code](errors.md#exit-codes) by kind: `3` not signed in, `4` re-read and retry.
- **Prompts on stderr.** `coho login` writes its URL and asks for its code on stderr, so
  they reach a person even when stdout is piped.
- **No sign-in by an agent.** Signing in needs a browser and a password, and on a
  machine with no browser a code pasted back by hand: a person runs `coho login`. With
  no terminal to paste into, it fails at once with `AUTH_NO_TERMINAL`. An agent should
  never ask for the code, which the sign-in page warns about.
- **`--help` links the docs.** Every command's help ends with a link to its page here.
