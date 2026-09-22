# Changelog

## 0.1.0 — unreleased

Initial version.

- `coho_sdk`: `Coho` → `Account` → `Project` → `Ref` object model over the BFF;
  problem documents mapped to `CohoError` subclasses by `code`; ETags carried by
  `Entry`/`ContentType`; PKCE login with keyring/file token stores and silent refresh;
  profiles and sticky context in `~/.config/coho/config.toml`; `coho_sdk.testing.FakeBff`.
- `coho`: login/logout/whoami/signup/configure/profile, use/status, account, member,
  invite, user, project (with a local registry — the server has no listing yet), role,
  ref, branch, tag, type, entry, diff, merge, env/promote/rollback, tier, key, export,
  preview. `--output json` prints the contract's response verbatim.
