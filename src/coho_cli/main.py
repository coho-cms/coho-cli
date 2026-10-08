"""The ``coho`` command.

Grammar borrowed from ``aws``: ``coho <noun> <verb> [--flags]``, ``--output json|table``.
Context borrowed from ``git``: ``coho use <account> [<project> [<ref>]]`` sticks.
"""

from __future__ import annotations

import sys
from typing import Annotated

import typer
from coho_management_sdk import CohoError
from coho_management_sdk import __version__ as sdk_version
from coho_management_sdk.errors import (
    AuthError,
    EnvironmentMoved,
    MergeConflict,
    NotFound,
    NotLoggedIn,
    PreconditionRequired,
    Unauthenticated,
    VersionConflict,
)
from coho_management_sdk.profiles import Context
from rich.console import Console
from rich.text import Text

from . import __version__
from ._output import console
from ._state import EXIT_AUTH, EXIT_CONFLICT, EXIT_ERROR, EXIT_NOT_FOUND, State, Usage
from .commands import (
    account,
    auth,
    branch,
    context,
    diffmerge,
    entry,
    env,
    export,
    invite,
    key,
    member,
    preview,
    project,
    ref,
    role,
    tag,
    tier,
    type_,
    user,
)

err = Console(stderr=True)

app = typer.Typer(
    name="coho",
    help="Manage Coho: accounts, projects, branches, releases and content.",
    no_args_is_help=True,
    add_completion=True,
    pretty_exceptions_enable=False,
    rich_markup_mode="markdown",
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _version(value: bool) -> None:
    if value:
        _print_version()
        raise typer.Exit()


# The mark's two bars in their dark-surface colours (brand rules: slate-dk over red-dk).
_MARK_UPPER = "on #8FA9BC"
_MARK_LOWER = "on #D9453F"


def _print_version() -> None:
    """The header: the mark beside the name where there is colour, plain lines where there is not.

    Rich decides: no colour when output is piped or NO_COLOR is set, and it steps the
    24-bit colours down on a terminal that cannot show them.
    """
    tagline = f"a CohoWorks project · v{__version__}"
    sdk = f"coho-management-sdk {sdk_version}"
    if console.color_system is None or console.no_color:
        console.print(f"CohoCMS\n{tagline}\n{sdk}", highlight=False)
        return
    bar = " " * 8
    console.print(Text.assemble((bar, _MARK_UPPER), "  ", ("CohoCMS", "bold")))
    console.print(Text.assemble((bar, _MARK_LOWER), "  ", (tagline, "dim")))
    console.print(Text.assemble(" " * len(bar), "  ", (sdk, "dim")))


@app.callback()
def _root(
    ctx: typer.Context,
    profile: Annotated[
        str | None, typer.Option("--profile", "-p", envvar="COHO_PROFILE", help="Profile to use.")
    ] = None,
    output: Annotated[
        str,
        typer.Option(
            "--output", "-o", envvar="COHO_OUTPUT", help="`table` for people, `json` for scripts."
        ),
    ] = "table",
    url: Annotated[
        str | None, typer.Option("--url", envvar="COHO_URL", help="Override the profile's BFF URL.")
    ] = None,
    account_: Annotated[
        str | None, typer.Option("--account", envvar="COHO_ACCOUNT", help="Account id or name.")
    ] = None,
    project_: Annotated[
        str | None,
        typer.Option("--project", envvar="COHO_PROJECT", help="Project id or known name."),
    ] = None,
    ref_: Annotated[
        str | None, typer.Option("--ref", envvar="COHO_REF", help="Branch, tag or environment.")
    ] = None,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="No confirmations on stdout.")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompts.")] = False,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version", "-V", callback=_version, is_eager=True, help="Print the version."
        ),
    ] = None,
) -> None:
    if output not in ("table", "json"):
        raise Usage("--output must be `table` or `json`")
    ctx.obj = State(
        profile_name=profile,
        output=output,
        url=url,
        overrides=Context(account=account_, project=project_, ref=ref_),
        quiet=quiet,
        yes=yes,
    )


# Top-level verbs (no noun): the ones people type most.
app.command("login")(auth.login)
app.command("logout")(auth.logout)
app.command("whoami")(auth.whoami)
app.command("signup")(auth.signup)
app.command("configure")(auth.configure)
app.command("use")(context.use)
app.command("status")(context.status)
app.command("diff")(diffmerge.diff)
app.command("merge")(diffmerge.merge)
app.command("promote")(env.promote)
app.command("rollback")(env.rollback)
app.command("export")(export.export)

# Nouns.
app.add_typer(auth.profile_app, name="profile")
app.add_typer(account.app, name="account")
app.add_typer(member.app, name="member")
app.add_typer(invite.app, name="invite")
app.add_typer(user.app, name="user")
app.add_typer(project.app, name="project")
app.add_typer(role.app, name="role")
app.add_typer(ref.app, name="ref")
app.add_typer(branch.app, name="branch")
app.add_typer(tag.app, name="tag")
app.add_typer(type_.app, name="type")
app.add_typer(entry.app, name="entry")
app.add_typer(env.app, name="env")
app.add_typer(tier.app, name="tier")
app.add_typer(key.app, name="key")
app.add_typer(preview.app, name="preview")


def _exit_code(exc: CohoError) -> int:
    if isinstance(exc, NotLoggedIn | AuthError | Unauthenticated):
        return EXIT_AUTH
    if isinstance(exc, VersionConflict | MergeConflict | EnvironmentMoved | PreconditionRequired):
        return EXIT_CONFLICT
    if isinstance(exc, NotFound):
        return EXIT_NOT_FOUND
    return EXIT_ERROR


def _print_error(exc: CohoError) -> None:
    # The bare message, not str(exc): CohoError's own text already starts with the
    # code, and this line prints the code itself.
    message = exc.detail or exc.title or (str(exc.args[0]) if exc.args else exc.code)
    err.print(f"[red]error[/red] [bold]{exc.code}[/bold]: {message}", highlight=False)
    if isinstance(exc, MergeConflict) and exc.conflicts:
        err.print("conflicts:")
        for c in exc.conflicts:
            where = f" at {', '.join(c.get('paths') or [])}" if c.get("paths") else ""
            err.print(
                f"  {c.get('slug') or c.get('nodeId')}: {c.get('reason')}{where}", highlight=False
            )
        err.print(
            "Resolve them with `coho merge … --resolve resolutions.json` "
            "(see docs/commands/merge.md)."
        )
    elif isinstance(exc, VersionConflict):
        err.print("Re-read the entry and retry, or pass --force to overwrite the current version.")
    elif isinstance(exc, PreconditionRequired):
        err.print("Pass --if-match <etag> from your last read, or --force to overwrite.")
    elif isinstance(exc, NotLoggedIn):
        err.print("Run `coho login`, or set COHO_ACCESS_TOKEN.")
    errors = exc.context.get("errors")
    if isinstance(errors, list) and errors:
        for e in errors:
            err.print(f"  {e.get('path', '')}: {e.get('message', '')}", highlight=False)
    for key_ in (
        "permission",
        "ref",
        "slug",
        "limit",
        "current",
        "expectedVersion",
        "currentVersion",
    ):
        if key_ in exc.context:
            err.print(f"  {key_}: {exc.context[key_]}", highlight=False)


def main() -> None:
    """Console-script entry point: run the app, print errors without tracebacks."""
    try:
        app(standalone_mode=True)
    except Usage as exc:
        err.print(f"[red]error[/red]: {exc.message}", highlight=False)
        sys.exit(exc.exit_code)
    except CohoError as exc:
        _print_error(exc)
        sys.exit(_exit_code(exc))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":  # pragma: no cover
    main()
