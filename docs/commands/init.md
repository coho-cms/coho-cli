# init

Files a repository keeps about its Coho project. For now, one: `COHO.md`, for coding
agents. See [coding agents](../agents.md) for how it fits with the Claude Code plugin.

## `coho init --agents [--dir DIR] [--ref REF] [--check]`

Reads the live project and writes `COHO.md` into the repository (`--dir`, the current
folder by default):

- the server, the account and project, by name and id, and the trunk, so every command an
  agent runs can name this project rather than rely on a machine's saved context;
- the rules for changing content: `-o json`, read before write, the ETag on every
  replacing write, exit code 4 means re-read, write on a branch, and never merge, tag,
  promote or roll back;
- the branches, the environments and what each points at, and the latest ten tags;
- the locales in use, read from the first 500 entries, since Coho keeps no list of
  locales;
- every content type and component type on the ref, with every field it has (inherited
  and from traits included), each field's type, whether it is required or localized, its
  choices, the types it references, its bounds, and the help text its editor shows;
- the traits, and commands for this project, with its own slugs and field ids.

It reads and never writes to Coho. It records no person: if a project token is in use
(`COHO_TOKEN`), it records the token's label and role, since a token belongs to the
project.

`AGENTS.md` and `CLAUDE.md` get a marked block pointing at `COHO.md`, between
`<!-- BEGIN:coho-agent-rules -->` and `<!-- END:coho-agent-rules -->`, merged the way
`next dev` merges its own block: replaced where it stands, appended where it is not,
and nothing outside the markers is touched, line endings included.

| The repository has | It writes |
|---|---|
| neither file | `AGENTS.md` with the block, and `CLAUDE.md` as `@AGENTS.md` |
| `AGENTS.md` | the block in `AGENTS.md`; `CLAUDE.md` as `@AGENTS.md` if there is none, or the block in it too if it does not import `AGENTS.md` |
| only `CLAUDE.md` | the block in `CLAUDE.md` |

The block ends with `@COHO.md`, which Claude Code reads as an import; other agents read
the file it names.

**Which project.** `--account` and `--project` (or `COHO_ACCOUNT`, `COHO_PROJECT`) when
given. Else the one an existing `COHO.md` names, so regenerating describes the same
project on any machine, whatever context it has saved. Else the one `coho.config.json`
names, for [`@coho-cms/codegen`](https://www.npmjs.com/package/@coho-cms/codegen). Else
the saved context. It warns when the recorded server is not the one the profile reaches.

**Which ref.** The types are read from the trunk, or `--ref`. A `--ref` is recorded, and
used again on the next run.

**Regenerating.** Run it again after the content model changes, and commit what it
writes: a difference is the model having changed. The file is deterministic, with no
timestamps or entry counts, so an unchanged project rewrites nothing. Its ids, its
environments' targets and its tags change only when the project does.

`--check` writes nothing and exits 1, naming the files, when they are not what it would
write. It suits CI, with a read-only project token:

```bash
COHO_TOKEN=$COHO_READ_TOKEN coho init --agents --check
```

```
coho init --agents
coho init --agents --dir site --ref v1.2.0
```

`--output json` prints each file's outcome (`created`, `updated`, or `unchanged`), the
ids, the ref, the counts of content and component types, and the locales.
