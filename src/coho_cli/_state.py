"""What every command needs: the config, the profile, a client, and the context.

Resolution order for the three context values (account, project, ref):
``--account/--project/--ref`` flags → ``COHO_ACCOUNT/COHO_PROJECT/COHO_REF`` →
the profile's saved context (``coho use``). A missing value is a usage error that
names the flag and the ``use`` command, not a stack trace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from uuid import UUID

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
        if name:
            return self.coho.account(name)
        # No account chosen. Someone in exactly one account has nothing to choose,
        # so that one is used; with several, guessing would act on the wrong one.
        memberships = self.coho.accounts()
        if len(memberships) == 1:
            return self.coho.account(memberships[0].account_id)
        if not memberships:
            raise Usage(
                "you are not in any account yet. Create one with `coho signup`, "
                "or ask an account admin to invite you."
            )
        names = ", ".join(sorted(m.account_name for m in memberships))
        raise Usage(
            f"you are in {len(memberships)} accounts ({names}). "
            "Choose one with `coho use <account>` or pass --account."
        )

    def project(self) -> Project:
        account = self.account()
        raw = self.context.project
        if not raw:
            raise Usage(
                "no project in context. Run `coho use <account> <project>` or pass --project."
            )
        return account.project(self.resolve_project_id(account, raw))

    def resolve_project_id(self, account: Account, raw: str) -> str:
        """A project id from an id, a locally remembered name, or a name on the server.

        The local registry answers first and without a request; an id passes
        through; anything else is matched by name against the projects the server
        lists for you. Two projects with the same name are refused rather than
        guessed between.
        """
        known = self.profile.resolve_project(account.id, raw)
        if known != raw or _is_uuid(raw):
            return known
        matches = [p for p in account.projects.list() if p.name.casefold() == raw.casefold()]
        if len(matches) == 1:
            return matches[0].id
        if not matches:
            raise Usage(f"no project named '{raw}' that you can open. See `coho project list`.")
        ids = ", ".join(p.id for p in matches)
        raise Usage(f"{len(matches)} projects are named '{raw}' ({ids}). Use the id.")

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


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True
