# Changelog

All notable changes to `coho-cli`. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[semantic versioning](https://semver.org/).

## [Unreleased]

## [2026.2.4] — 2026-11-10

### Added

- `coho webhook create --github OWNER/NAME --token TOKEN`: a webhook that starts the
  repository's GitHub Actions workflows through `repository_dispatch`, with each event as its
  `client_payload` (coho-data doc 70 WH-17). It has no signing secret, so nothing is printed
  once. `--token -` reads the token from standard input. `coho webhook update` takes
  `--github` and `--token`, which is how its token is replaced; `show` and `list` name its
  repository.
- `coho entry put --slug SLUG` renames an entry, alone or with `--set` or `--file`, in the same
  version as the save. `SLUG_CONFLICT` if another entry on the ref holds it.
- `coho env delete NAME --reason TEXT` (`-m`): kept in the environment's history after the
  word `deleted`.

### Changed

- `coho webhook create`'s `--url` is no longer required, since a GitHub webhook has none; one
  of `--url` or `--github` is.
- Needs `coho-management-sdk` 2026.2.4 or later.

## [2026.2.3] — 2026-11-09

Everything since 2026.2.0, so this includes what shipped as 2026.2.1, which had no section of
its own.

### Added

- `coho branch delete` and `coho tag delete` (coho-data doc 76). A deleted branch's name is free
  again; a deleted tag's never is, since a release may be cached under it for a year. A branch
  that has not been merged asks a second time, or takes `--confirm-destructive` with `--yes`.
  `coho branch list` shows `changed` for a branch merged and written to since.
- `coho ref deleted` and `coho ref restore` (coho-data doc 77): see what has been deleted, and
  bring it back. An owner's or an organization admin's.

- The `coho` skill knows Coho's MCP server (coho-data doc 75). When tools from a server
  named `coho` are available, it uses them for content work rather than the CLI, with a
  table from each command to its tool. It says what to do when the connection lacks a
  scope or needs signing in, and that every tool needs a ref, as no project has a `main`.
  It never calls `merge`, `create_tag`, `promote`, `rollback`, or `create_version_branch`,
  and asks before `delete_entry` and `put_type`. The CLI stays the way to `COHO.md`, roles,
  tokens, keys, and webhooks. The plugin's descriptions now name both.

- `coho login` on a machine with no browser (coho-data doc 73). `--no-browser` now means
  open the URL in any browser, anywhere, and paste back the code the sign-in's last page
  shows; before, the sign-in still came back to `localhost:8765` and could finish only on
  the same machine. It is the default, saying why, over SSH (`SSH_CONNECTION` or
  `SSH_TTY`) and on Linux with no `DISPLAY` or `WAYLAND_DISPLAY`. `--port` keeps the
  loopback flow for a tunnel, and prints the URL with the `ssh -L` it needs. With no
  terminal to paste into, it fails at once with `AUTH_NO_TERMINAL` (exit 3). Needs
  `coho-management-sdk` with `login(mode="paste")` and a sign-in service with `/cli/code`.

- `coho status` shows the credential in use (a person, from `coho login` or a stored
  token; or a project token, with its label and expiry), your account role, your project
  role, and that role's permissions, so a person, a script, or an AI agent can tell what
  it may do in the current context before trying. `--output json` gives them as
  `credential`, `accountRole`, `projectRole`, and `permissions`.
- `coho init --agents` writes `COHO.md` from the live project, for coding agents: its ids,
  every content type and component type with every field (required, localized, choices,
  references, bounds, editor help), the locales its entries use, its branches,
  environments and tags, and the rules for changing content (`-o json`, read before
  write, the ETag on every replacing write, exit 4 means re-read, write on a branch,
  never merge, tag, promote or roll back). `AGENTS.md` and `CLAUDE.md` get a marked block
  pointing at it, merged the way `next dev` merges its own. Regenerating describes the
  project an existing `COHO.md` names (or `coho.config.json`, for `@coho-cms/codegen`),
  and `--check` exits 1 when the files are out of date. See `docs/agents.md`.
- `--help` on every command ends with a link to its page in `docs/` on GitHub.
- A Claude Code plugin with a `coho` skill, in this repository (`.claude-plugin/`,
  `skills/coho/SKILL.md`): `/plugin marketplace add coho-cms/coho-cli`, then
  `/plugin install coho@coho-cms`. It teaches Claude to start from `coho status`, keep to
  what the role allows, read `COHO.md`, leave signing in and releasing (merge, tag,
  promote, rollback) to the user, and ask before deleting, granting, or making a secret.
  It pre-approves only commands that read.

### Changed

- `--output` defaults to `json` when stdout is not a terminal (a pipe, a file, an agent
  capturing output), and to `table` on one. `--output` or `COHO_OUTPUT` still chooses.
  `coho login`'s prompts (the URL, the code) go to stderr, so they reach you when stdout
  is piped.
- `coho role ladder` reads the roles from `coho-management-sdk`, and so now shows
  `promote:preview` for `author`, which the server has granted all along.
- `coho login`, `coho signup`, and `coho invite accept` print the URL when there is no
  browser to open, or opening one fails, rather than saying nothing.

### Fixed

- Needs `coho-management-sdk` 2026.2.3, which keeps out httpx 1.0's pre-releases. With
  those, an install that allowed pre-releases failed with a `TypeError` on every command
  that calls the API.

## [2026.2.0] — 2026-11-03

The first release out of alpha. Everything below shipped across the 2026.1.0 alphas.

### Changed

- A new profile points at Coho's production service: `url = https://api.coho-cms.com`,
  `oidc_domain = https://auth.coho-cms.com`, `client_id = coho-cli`. `coho configure`
  with no flags is a working production profile, and on a machine with no config file the
  first command resolves `default` to the same thing without writing one, so a fresh
  install is `coho login` and nothing before it. `--url` and `--oidc-domain` still win,
  and an existing profile is never rewritten, so one pointed at dev stays pointed at dev.
  A profile that was *asked* for and is missing is still an error: `-p prod` on a fresh
  machine says to create `prod` rather than inventing it.

### Fixed

- `coho profile show` printed a traceback instead of an error when the profile did not
  exist.

### Added

- `coho webhook` (coho-data doc 70): `list`, `events`, `create`, `show`, `update`,
  `delete`, `rotate`, `test`, `deliveries`, `delivery`, and `redeliver`, the endpoints Coho
  calls when something happens in the project, for parity with the portal's Webhooks page.
  `create` and `rotate` print the signing secret once, and `rotate` says when the previous
  one stops signing; `update --header` replaces every custom header, since their values
  cannot be read back. `deliveries` reads the log, filtered by state, event type, and
  time; `delivery` shows each attempt's status, failure, time taken, and response; and
  `redeliver` sends one delivery again, or every one that failed since `--failed-since`.
  Owners only, at most 25. A webhook's or a delivery's id is never cut short in a table, so
  it can be copied from a narrow terminal into the next command. Needs coho-management-sdk
  with `project.webhooks`.
- `coho pin list`, `add`, `remove` and `order` (coho-data doc 67): your pinned entries in
  the current project, the ones the console keeps at hand, for parity with it. A pin is
  yours alone and the project's, not a ref's, so `pin list` shows each as it reads on the
  current ref: live, deleted here, or not on this ref. Any role may pin, at most 20
  (`PIN_LIMIT`); `pin order` names every pin once, top first. Needs coho-management-sdk
  with `project.pins`.
- Singleton types (coho-data doc 66). `coho entry create -t siteSettings` with no `--slug`
  leaves the slug to the server, which gives a singleton's entry its fixed slug,
  `site-settings`, where any other type's slug is still built from `_name`. Wherever a
  command takes an entry `ID`, a singleton type's slug names its one entry: `coho entry
  get siteSettings`. A type of many entries is refused as an id. Needs
  coho-management-sdk with `entries.create(slug=None)`.
- `--at SEQ` on the commands that read a ref (coho-data doc 59 HI-4): `entry list`, `get`,
  `history` and `references`, `type list` and `get`, `trait list` and `get`, and `asset
  list` and `get`. Each reads the ref as it was at that seq, the `SEQ` that `coho entry
  history` prints, so an old version of an entry comes back with its type as it was. On a
  tag it may go back but not past the tag; out of range is `AT_OUT_OF_RANGE`. Needs
  coho-management-sdk with `project.ref(name, at=…)`, and a server with `at` on reads.
- `coho project rename NAME` (coho-data doc 39 §11.1): renames the current project, an
  account admin's. Only the name changes — its id, delivery URLs, keys and tokens are
  untouched — and an archived project can be renamed too. The local registry drops the old
  name and records the new one, because the server frees the old name for another project
  to take. Needs coho-management-sdk with `Project.rename`.
- `coho tier move ID --ord N` (coho-data doc 11, M6-15): moves a tier in the pipeline, and
  the tiers it passes shift by one. Needs coho-management-sdk with `tiers.move`.
- `coho trait list`, `get`, `put` and `delete` (coho-data doc 05 §10): traits, named groups
  of fields that types take by naming them in `traits`. `trait list` shows the types that
  take each. A refused trait or type change now prints what it reaches, `reaches: page,
  servicePage, and 12 entries`, and a trait in use is refused with the types that take it.
- `coho type get` shows the type it extends, the traits it takes, and whether it is
  abstract (coho-data doc 05 §9).

### Changed

- A project remembered under more than one name is now **named** by the newest of them,
  where before it was the one remembered first. A project renamed anywhere — the console,
  the SDK, another machine — was reported by `coho status` and `coho context show` under
  its old name indefinitely.
- `coho tier create --ord N` inserts: a position another tier holds moves that tier and the
  ones after it along, where it was refused with `TIER_ORDER_TAKEN`, and anything past the
  end is the end (coho-data doc 11, M6-15). `coho tier delete` closes the gap it leaves.

### Fixed

- Output redirected to a file or a pipe on Windows, or written under a non-UTF-8 locale
  elsewhere, ended in `UnicodeEncodeError` for anything with box drawing or non-ASCII
  text, `coho --help` included. `coho` now always writes UTF-8, and replaces with `?`
  anything it still cannot write.
- An `@slug` in a field a type inherits, or takes from a trait, is written as the id it
  names: `coho entry create -t photoGallery --set author=@tom-okafor` stored the text
  `@tom-okafor`, because the slug was looked up only in the fields the type declares itself.
- Component types (coho-data doc 40 §14.10): `coho type put` takes a definition with
  `"kind": "component"`, and `type list`, `get` and `put` show each type's `KIND`. A
  repeater takes its items as a JSON list, `--set 'citations=[{…}]'`, and the server
  assigns each item's `_id` and, where the repeater holds one component, its `_type`.
  Needs coho-management-sdk with `ContentType.kind` and a server with component types.

- `coho project usage [PROJECT]` and `coho account usage`: metered usage (coho-data doc
  41), as a table or, with `-o json`, the report exactly as the server sent it. A
  project's shows delivery by key with requests per distinct URL (the client that is not
  caching), management by people and project tokens and by class, content, history and
  assets; anyone who can read the project may, project tokens included. The account's
  sums every project and lists each one's totals, for admins: a member's `FORBIDDEN`
  says to use `coho project usage` instead. Both take `--grain hour|day`, `--from`,
  `--to`, `--meter` (repeatable) and `--periods` for a line per hour or day. Needs
  coho-management-sdk with `usage()` and a server with the usage routes.

- `coho preview entries` ends the table with `more: --offset N` when another page
  follows, as `entry list` does. It has no `--all`, because each live page resolves the
  whole ref.
- `@SLUG` wherever a command takes an entry id: `entry get`, `put`, `delete`, `history`,
  `references` and `preview entry`. The slug is looked up on the same ref with one
  request (the BFF's live `preview/{ref}/entries-by-slug/{slug}`), then the command runs
  as if the id had been typed; a plain id is used as given. A slug nothing has is
  `ENTRY_NOT_FOUND` (exit 5); one that names a type or an asset, or `@` before something
  that is not a slug, is a usage error. `entry delete @SLUG` asks about both the slug and
  the id it found. `entry list` and `entry get` show the slug from `_slug` while the
  server's entry responses leave out `slug`.
- `@SLUG` in a reference field's `--set` value, on `entry create` and `entry put`:
  `--set author=@priya-shah --set 'tags=["@traffic"]'` writes the ids those slugs name
  on the same ref. Only fields the content type declares as references are looked up, so
  text keeps a leading `@`; the type is read only when a value starts with `@`.
- `@SLUG` in an asset field's `--set` value too: `--set image=@culvert` writes the id of
  the asset with that slug, from one listing of the ref's assets. A slug no asset has
  is `ASSET_NOT_FOUND` (exit 5).
- `coho ref switch NAME`: makes a branch, tag or environment of the current project the
  current ref, after checking it exists, keeping the account and project. It and
  `coho branch create` warn when `--ref` or `COHO_REF` still overrides the saved ref.
- `coho asset`: files on the current ref (coho-data doc 40). `asset upload FILE…` hashes
  each file, sends it straight to object storage on a presigned URL and writes it as an
  asset, building the slug from the filename (`Hero Shot.jpg` → `hero-shot`) unless
  `--slug` is given for a single file; `--title`, `--alt`, `--focal x,y` and `--tag` set
  its metadata. Bytes the project already holds are not sent again. Also `asset list`,
  `get`, `url` (prints the original, or a resized image URL with `--width`, `--height`,
  `--fit`, `--format`, `--quality`, centring fills on the focal point), `put` and
  `delete`, each taking an id or a slug. Upload warns on stderr that asset URLs are
  public to anyone holding them. Needs the `coho-management-sdk` that adds `ref.assets`,
  and a server with the asset routes.
- On PyPI: `uv tool install coho-cli` or `pipx install coho-cli`.
- `coho login` finishes setting up an identity that has no organization yet: it opens the
  BFF's sign-in in the browser, which asks for the organization's name, and waits until the
  account exists. That sign-in asks for the password once more, because the CLI's own sign-in
  never reaches the BFF. `coho login --token` with such an identity says where to go instead.
- An account saved with `coho use` that is not one of yours any more — deleted, or
  remembered from before an environment was reset — gives way to your only account, which
  is saved in its place (with the stale project and ref cleared) and named in a one-time
  warning. With several accounts it asks which. Costs one `/me` per command while an
  account is saved. `--account` and `COHO_ACCOUNT` are used as given.
- `coho type put` and `coho entry create` build the slug from the name when none is given:
  camelCase for a type (`Blog post` → `blogPost`), kebab-case for an entry (`Hello, World!` →
  `hello-world`). An explicit slug is sent unchanged.
- `coho tag create --validate` has the server check every entry at the tag point before
  cutting the tag. If any fails, it is refused with `TAG_CONTENT_INVALID` and nothing is
  tagged: the CLI prints how many entries fail, then each listed one's slug, type, id and
  field errors, says how many went unlisted past the server's 100, and exits 1. With
  `-o json` the problem document goes to stdout. Without the flag, tagging is unchanged.
  Needs the `coho-management-sdk` that adds `tags.create(validate=…)`, and a server that
  accepts `validate`.

### Changed

- `coho branch create` makes the new branch the current ref, as `coho project create`
  makes the new project current; `--no-use` keeps the current ref. When `--ref` or
  `COHO_REF` is set, it warns that the override still wins over the saved ref.
- `coho signup` opens the BFF's sign-up page in the browser, as `coho login` opens the
  sign-in page, and makes no API call itself. Sign-up stays an interactive session;
  before release that page verifies a captcha.
- `coho login` uses `http://localhost:8765/callback`, matching the CLI's Cognito app
  client, and answers on both loopback addresses.

- The library moved to its own repository and distribution,
  [coho-management-sdk-python](https://github.com/coho-cms/coho-management-sdk-python), along with the API
  contracts and the library reference. This repository is now the command alone, and
  depends on `coho-management-sdk` as an ordinary package. Development uses a sibling checkout;
  see [CONTRIBUTING.md](CONTRIBUTING.md).

### Fixed

- `coho preview entries` crashed with `AttributeError: 'str' object has no attribute
  'get'`, in table and JSON output both. It read the body as a list of entries, but
  delivery answers with an `EntryGraph`: it now lists `roots` in order, looked up in
  `entries`.
- `coho signup`, `coho invite lookup` and `coho invite accept` failed with
  `NOT_LOGGED_IN` for anyone without a login, who are exactly the people they are for.
- Errors printed their code twice, as in `error NOT_LOGGED_IN: NOT_LOGGED_IN: …`.
- URLs printed by `--no-browser` were wrapped at the terminal's width, so a copied URL
  came out broken.
- `coho login` followed a successful sign-in with a bare `UNAUTHENTICATED` when the
  identity had no Coho account yet. It now says so, and what to run.

## [0.1.0] — unreleased

Initial version.

- Commands: `login`, `logout`, `whoami`, `signup`, `configure`, `profile`, `use`,
  `status`, `account`, `member`, `invite`, `user`, `project`, `role`, `ref`, `branch`,
  `tag`, `type`, `entry`, `diff`, `merge`, `env`, `promote`, `rollback`, `tier`, `key`,
  `export`, `preview`.
- A sticky context (account, project, ref) per profile, verified against the server
  before it is saved, and overridable by flag or environment variable.
- `--output json` prints the contract's response verbatim, so `jq` works against the
  documented shapes. Exit codes distinguish usage (2), authentication (3), a failed
  precondition worth retrying (4) and not-found (5).
- A local project registry, because the server has no project listing yet.

[Unreleased]: https://github.com/coho-cms/coho-cli/compare/release-v2026.2.4...HEAD
[2026.2.4]: https://github.com/coho-cms/coho-cli/releases/tag/release-v2026.2.4
[2026.2.3]: https://github.com/coho-cms/coho-cli/releases/tag/release-v2026.2.3
[2026.2.0]: https://github.com/coho-cms/coho-cli/releases/tag/v2026.2.0
[0.1.0]: https://github.com/coho-cms/coho-cli/releases/tag/v0.1.0
