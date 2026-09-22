"""What every command needs: the config, the profile, a client, and the context.

Resolution order for the three context values (account, project, ref):
``--account/--project/--ref`` flags → ``COHO_ACCOUNT/COHO_PROJECT/COHO_REF`` →
the profile's saved context (``coho use``). A missing value is a usage error that
names the flag and the ``use`` command, not a stack trace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property

import typer
from coho_management_sdk import Account, Coho, Config, Profile, Project, Ref
from coho_management_sdk.profiles import Context

EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_AUTH = 3
EXIT_CONFLICT = 4
EXIT_NOT_FOUND = 5


class Usage(Exception):
    """A usage error: printed as one line by ``main()``, exit code 2, no traceback."""

    exit_code = EXIT_USAGE

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class State:
    profile_name: str | None = None
    output: str = "table"
    url: str | None = None
    overrides: Context = field(default_factory=Context)
    quiet: bool = False
    yes: bool = False

    @cached_property
    def config(self) -> Config:
        return Config.load()

    @cached_property
    def profile(self) -> Profile:
        try:
            return self.config.profile(self.profile_name)
        except KeyError as exc:
            name = exc.args[0]
            raise Usage(
                f"no profile named '{name}'. Create it: coho configure --profile {name} --url https://…"
            ) from exc

    @property
    def context(self) -> Context:
        saved = self.profile.context.with_env()
        return Context(
            account=self.overrides.account or saved.account,
            project=self.overrides.project or saved.project,
            ref=self.overrides.ref or saved.ref,
        )

    @cached_property
    def coho(self) -> Coho:
        url = self.url or self.config.effective_url(self.profile)
        if not url:
            raise Usage(
                f"profile '{self.profile.name}' has no url. Set one: "
                f"coho configure --profile {self.profile.name} --url https://…"
            )
        return Coho(url, profile=self.profile)

    # -- context resolution ----------------------------------------------------

    def account(self) -> Account:
        name = self.context.account
        if not name:
            raise Usage("no account in context. Run `coho use <account>` or pass --account.")
        return self.coho.account(name)

    def project(self) -> Project:
        account = self.account()
        raw = self.context.project
        if not raw:
            raise Usage(
                "no project in context. Run `coho use <account> <project>` or pass --project."
            )
        project_id = self.profile.resolve_project(account.id, raw)
        return account.project(project_id)

    def ref(self) -> Ref:
        project = self.project()
        name = self.context.ref
        if not name:
            raise Usage(
                "no ref in context. Run `coho use <account> <project> <ref>` or pass --ref."
            )
        return project.ref(name)

    def save(self) -> None:
        self.config.save()


def get_state(ctx: typer.Context) -> State:
    state = ctx.find_root().obj
    if not isinstance(state, State):  # pragma: no cover - typer wiring
        state = State()
        ctx.find_root().obj = state
    return state
