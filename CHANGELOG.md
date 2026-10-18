# Changelog

All notable changes to `coho-cli`. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[semantic versioning](https://semver.org/).

## [Unreleased]

### Added

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
