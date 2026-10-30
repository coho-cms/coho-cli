# Changelog

All notable changes to `coho-cli`. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[semantic versioning](https://semver.org/).

## [Unreleased]

### Added

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

[Unreleased]: https://github.com/coho-cms/coho-cli/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/coho-cms/coho-cli/releases/tag/v0.1.0
