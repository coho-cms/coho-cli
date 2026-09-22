# Changelog

All notable changes to `coho-cli`. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[semantic versioning](https://semver.org/).

## [Unreleased]

### Changed

- The library moved to its own repository and distribution,
  [coho-management-sdk-python](https://github.com/coho-cms/coho-management-sdk-python), along with the API
  contracts and the library reference. This repository is now the command alone, and
  depends on `coho-management-sdk` as an ordinary package. Development uses a sibling checkout;
  see [CONTRIBUTING.md](CONTRIBUTING.md).

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
