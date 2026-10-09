# Command reference

```
coho [global options] <command> [args]
coho [global options] <noun> <verb> [args]
```

Global options: `-p/--profile`, `-o/--output table|json`, `--url`, `--account`,
`--project`, `--ref`, `-q/--quiet`, `-y/--yes`, `-V/--version`. See
[configuration](../configuration.md).

| Page | Commands |
|---|---|
| [auth](auth.md) | `login`, `logout`, `whoami`, `signup`, `configure`, `profile list/show/use/delete` |
| [context](context.md) | `use`, `status` |
| [account](account.md) | `account list/show/rename/entitlements/events/plans` |
| [member](member.md) | `member list/role/remove/leave` |
| [invite](invite.md) | `invite create/list/revoke/lookup/accept` |
| [user](user.md) | `user rename/logins/detach-login` |
| [project](project.md) | `project create/show/list/register/forget` |
| [role](role.md) | `role list/grant/revoke/ladder` |
| [ref](ref.md) | `ref list/show/describe` |
| [branch](branch.md) | `branch list/create` |
| [tag](tag.md) | `tag list/create` |
| [type](type.md) | `type list/get/put/delete` |
| [entry](entry.md) | `entry list/get/create/put/delete/history/references` |
| [diff](diff.md) | `diff` |
| [merge](merge.md) | `merge` |
| [env](env.md) | `env list/show/create/unset/delete/history`, `promote`, `rollback` |
| [tier](tier.md) | `tier list/create/delete` |
| [key](key.md) | `key create/list/revoke/public` |
| [token](token.md) | `token create/list/revoke` — project tokens for automation |
| [export](export.md) | `export` |
| [preview](preview.md) | `preview entries/entry` |

Every command accepts `-h`. In `--output json` mode each command prints the server's
response as the contract describes it (the contracts are vendored in the
[library repository](https://github.com/coho-cms/coho-management-sdk-python/tree/main/contracts));
the tables below describe the human output.
