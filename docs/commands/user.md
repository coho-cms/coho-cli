# user

Acting on yourself. Needs only the `coho-auth/self` scope.

| Command | What it does |
|---|---|
| `user rename DISPLAY_NAME` | `PATCH /api/v1/users/{me}` — email is not editable (`EMAIL_NOT_EDITABLE`) |
| `user logins` | identities attached to you: id, provider, subject |
| `user detach-login LOGIN_ID` | detach one; refused for your only one (`LAST_LOGIN`). Asks; `-y` to skip |

Attaching a second identity needs a second OIDC round trip with an attach intent,
which the BFF does not offer yet.
