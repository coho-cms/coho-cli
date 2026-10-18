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
from coho_management_sdk.models import Membership
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
    # Set when the account came from the saved context rather than `--account`, so an
    # ACCOUNT_NOT_FOUND can say the saved one may be gone: deleted, or a reset environment.
    used_saved_account: bool = field(default=False, init=False)
    # What to say after a 403, when the command knows better than the server's message
    # what the person can do instead.
    forbidden_hint: str | None = field(default=None, init=False)

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
        # Named on the command line or in COHO_ACCOUNT: used as given, never second-guessed.
        if self.overrides.account:
            return self.coho.account(self.overrides.account)
        name = self.context.account
        # ⚠️ A saved account can outlive the account: deleted, or an environment reset. Checked
        # against `/me` (one request, cached for the command) so a person with one account is
        # not stuck on one they no longer have. Not with a project token: it has no `/me`.
        if name and not self.coho.uses_project_token:
            memberships = self.coho.accounts()
            if not any(name in (m.account_id, m.account_name) for m in memberships):
                return self._instead_of_gone(name, memberships)
        if name:
            self.used_saved_account = True
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

    def _instead_of_gone(self, gone: str, memberships: list[Membership]) -> Account:
        """The saved account is not one of the caller's: their only one if they have one,
        saved in its place, or a usage error that says what to choose."""
        from ._output import warn

        # Only ever the profile's: `--account` and COHO_ACCOUNT (its envvar) are used as given.
        p = self.profile.name
        if not memberships:
            raise Usage(
                "you are not in any account yet. Create one with `coho signup`, "
                "or ask an account admin to invite you."
            )
        if len(memberships) > 1:
            names = ", ".join(sorted(m.account_name for m in memberships))
            raise Usage(
                f"the account saved for profile '{p}' is not one of yours; it may have been "
                f"deleted. You are in {len(memberships)} accounts ({names}): choose one with "
                "`coho use <account>`."
            )
        only = memberships[0]
        # As `coho use` does when the account changes: the project and ref were the gone account's.
        self.profile.context.account = only.account_id
        self.profile.context.project = None
        self.profile.context.ref = None
        self.save()
        warn(
            f"the account saved for profile '{p}' is not one of yours; it may have been "
            f"deleted. Using {only.account_name}, your only account, from now on."
        )
        return self.coho.account(only.account_id)

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
            raise Usage("no ref in context. Run `coho ref switch <ref>` or pass --ref.")
        return project.ref(name)

    def save(self) -> None:
        self.config.save()


# The running command's state, for `main` to read once an error has escaped the command.
current: State | None = None


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
