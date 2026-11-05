"""login, logout, whoami, signup, configure, profile."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from typing import Annotated

import typer
from coho_management_sdk import auth as sdk_auth
from coho_management_sdk.client import PROJECT_TOKEN_PREFIX
from coho_management_sdk.errors import AuthError, NotLoggedIn, Unauthenticated
from coho_management_sdk.profiles import DEFAULT_SCOPES, Profile

from .._browser import no_browser_reason, open_or_print, print_url
from .._defaults import PRODUCTION_OIDC_DOMAIN, PRODUCTION_URL, point_at_production
from .._output import console, err, record, say, table, warn
from .._state import State, Usage, get_state


class NoTerminal(AuthError):
    """`coho login` would ask for a pasted code, and there is no terminal to paste it into.

    coho-data doc 73 HL-8: a script cannot paste, and waiting five minutes for it helps
    nobody, so this fails at once and names the ways a script signs in.
    """

    code = "AUTH_NO_TERMINAL"


# How often `coho login` asks whether the account exists yet, while the person finishes
# setting it up in a browser. A module constant so a test can shorten it.
ACCOUNT_POLL_SECONDS = 3.0


def login(
    ctx: typer.Context,
    token: Annotated[
        str | None,
        typer.Option(
            "--token", help="Store this bearer token instead of running the browser flow."
        ),
    ] = None,
    no_browser: Annotated[
        bool,
        typer.Option(
            "--no-browser",
            help="Sign in from a browser anywhere, then paste the code it shows. "
            "The default over SSH, or on Linux with no display.",
        ),
    ] = False,
    port: Annotated[
        int | None,
        typer.Option(
            "--port",
            help="Loopback port for the callback (default: the profile's). "
            "Means the loopback flow, even over SSH: for a tunnel.",
        ),
    ] = None,
    timeout: Annotated[
        int, typer.Option("--timeout", help="Seconds to wait for the browser.")
    ] = 300,
) -> None:
    """Sign in to the current profile.

    Opens Coho's sign-in page in a browser (PKCE, no client secret) and stores the
    tokens in the OS keyring, or a 0600 file when there is none. Where there is no
    browser (`--no-browser`, an SSH session, Linux with no display), prints the URL to
    open anywhere and asks for the code the page shows. With `--token`, stores the given
    access token as-is — for a token obtained elsewhere.
    """
    state = get_state(ctx)
    profile = state.profile
    store = sdk_auth.token_store_for(profile)
    if token:
        store.save(profile.name, sdk_auth.TokenSet(access_token=token))
        if token.startswith(PROJECT_TOKEN_PREFIX):
            # A project token is not a person: there is no /me to confirm it with.
            say(
                state,
                f"Stored a project token for profile [bold]{profile.name}[/bold]. It works only "
                "for its project's content: set the account and project by id with `coho use`.",
            )
            return
        say(state, f"Stored a token for profile [bold]{profile.name}[/bold].")
    else:
        if not profile.can_login:
            raise Usage(
                f"profile '{profile.name}' has no identity provider configured. Either\n"
                f"  coho configure --profile {profile.name} --oidc-domain https://auth-…"
                " --client-id coho-cli\n"
                "or store a token you obtained elsewhere with `coho login --token …`."
            )

        if no_browser and port is not None:
            raise Usage(
                "--no-browser pastes a code; --port is for the loopback flow. Pass one of them."
            )
        # HL-6, HL-7: the flag, or plainly no browser here, means pasting a code. An
        # explicit --port means loopback whatever this machine looks like: a tunnel.
        headless = no_browser_reason()
        reason = None if port is not None else ("--no-browser" if no_browser else headless)
        # Asked once and kept for the organization step after (UL-19): --no-browser means
        # no browser opened by this command at all.
        browser_here = headless is None and not no_browser
        if reason is not None:
            tokens = _login_by_paste(profile, reason)
        else:
            tokens = _login_by_loopback(profile, browser_here, port, timeout)
        store.save(profile.name, tokens)
        say(state, f"Signed in to profile [bold]{profile.name}[/bold].")
        # Confirm the token works, and show who we are. An identity with no organization
        # finishes in the browser first (UL-19), and this waits for it there.
        _print_me(
            state,
            just_signed_in=True,
            finish=lambda: _finish_in_browser(state, not browser_here, timeout),
        )
        return
    _print_me(state, just_signed_in=True)


def _stdin_is_terminal() -> bool:
    """A function, so a test can say yes."""
    return sys.stdin.isatty()


def _login_by_paste(profile: Profile, reason: str) -> sdk_auth.TokenSet:
    """Copy the code (coho-data doc 73 §2): the URL here, the browser anywhere, the code back."""
    if not _stdin_is_terminal():
        raise NoTerminal(
            "there is no terminal here to paste a sign-in code into. In a script, use "
            "`coho login --token …`, or set COHO_ACCESS_TOKEN (or COHO_TOKEN for a project "
            "token)"
        )
    intro = (
        "Open this URL in any browser and sign in:"
        if reason == "--no-browser"
        else f"No browser here ({reason}); open this URL in any browser and sign in:"
    )

    # On stderr, like every prompt in `coho login`: the command's answer on stdout is who
    # you are, possibly as JSON into a pipe, and the person must see the prompt regardless.
    def read_code() -> str:
        return err.input("Then paste the code it shows: ")

    return sdk_auth.login(
        profile,
        mode="paste",
        read_code=read_code,
        on_url=lambda url: print_url(intro, url, to=err),
    )


def _login_by_loopback(
    profile: Profile, browser_here: bool, port: int | None, timeout: int
) -> sdk_auth.TokenSet:
    """The browser comes back to this machine's localhost: opened here, or through a tunnel."""
    listen = profile.callback_port if port is None else port
    intro = (
        "Open this URL in a browser and sign in:"
        if browser_here
        else f"Open this URL in a browser whose localhost:{listen} reaches this machine "
        f"(ssh -L {listen}:localhost:{listen} …), and sign in:"
    )

    def open_browser(url: str) -> None:
        if open_or_print(url, print_instead=not browser_here, intro=intro, to=err):
            err.print("Opened your browser to sign in… (or use --no-browser to paste a code)")

    return sdk_auth.login(profile, open_browser=open_browser, timeout=timeout, port=port)


def _finish_in_browser(state: State, no_browser: bool, timeout: int) -> None:
    """Send an identity with no organization to the BFF's sign-in, which asks for one (UL-19).

    The CLI signs in at the identity provider directly, so the BFF never saw this
    identity and cannot ask it anything; its own sign-in can. That means the password
    a second time, once, for an identity in this state. Then this waits for the account
    to exist, which is the same token answering `/me`.
    """
    url = state.coho.login_url()
    say(
        state,
        "Coho has no organization for this identity yet. Finish setting up in your browser: "
        "sign in there once more, then name your organization.",
    )
    open_or_print(url, print_instead=no_browser, intro="Open this URL in a browser:", to=err)
    say(state, "Waiting for your organization… (Ctrl-C to stop)")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(ACCOUNT_POLL_SECONDS)
        try:
            state.coho.me(refresh=True)
            return
        except Unauthenticated:
            continue
    raise Usage(
        "still no organization for this identity. Once you have named it in the browser, "
        "run `coho whoami`."
    )


def logout(ctx: typer.Context) -> None:
    """Forget the stored tokens for the current profile."""
    state = get_state(ctx)
    sdk_auth.token_store_for(state.profile).delete(state.profile.name)
    say(state, f"Logged out of profile [bold]{state.profile.name}[/bold].")


def whoami(ctx: typer.Context) -> None:
    """Who is signed in, and which accounts they belong to."""
    _print_me(get_state(ctx))


def _print_me(
    state: State,
    *,
    just_signed_in: bool = False,
    finish: Callable[[], object] | None = None,
) -> None:
    try:
        me = state.coho.me()
    except NotLoggedIn:
        raise Usage(f"not logged in to profile '{state.profile.name}'. Run `coho login`.") from None
    except Unauthenticated:
        if not just_signed_in:
            raise
        # The provider has just issued this token, so it is not stale. The auth
        # service gives UNAUTHENTICATED for an identity it has no account for
        # too, on purpose (LG-5), and right after a sign-in that is the likely one.
        if finish is None:
            raise Usage(
                "you signed in, but Coho has no account for this identity yet. Sign in at "
                f"{state.coho.login_url()} in a browser to name your organization, or accept "
                "an invitation to join one."
            ) from None
        finish()
        me = state.coho.me(refresh=True)
    if state.output == "json":
        record(state, me.raw, [])
        return
    record(
        state,
        me.raw,
        [
            ("user", me.user_id),
            ("name", me.display_name),
            ("email", me.email),
            ("profile", state.profile.name),
        ],
    )
    console.print()
    table(
        state,
        me.raw,
        ["ACCOUNT", "ID", "ROLE", "ACTOR"],
        [(a.account_name, a.account_id, a.role, a.actor_id) for a in me.accounts],
        empty="(no accounts — sign up or ask for an invitation)",
    )


def signup(
    ctx: typer.Context,
    account_name: Annotated[str, typer.Argument(help="Name of the new account to found.")],
    display_name: Annotated[str | None, typer.Option("--name", help="Your display name.")] = None,
    no_browser: Annotated[
        bool, typer.Option("--no-browser", help="Print the URL instead of opening it.")
    ] = False,
) -> None:
    """Create a new account, in the browser. Then run `coho login`.

    Opens the sign-up page, like `coho login` opens the sign-in page, and makes no
    API call itself: sign-up is an interactive browser session on purpose. You
    create your identity and verify your email there, and the page ends by showing
    your new account.
    """
    state = get_state(ctx)
    try:
        url = state.coho.signup_url(account_name, display_name=display_name)
    except ValueError as exc:
        raise Usage("the account name cannot be blank") from exc
    if open_or_print(
        url,
        print_instead=no_browser or no_browser_reason() is not None,
        intro="Open this URL in a browser to sign up:",
    ):
        say(state, "Opened the sign-up page in your browser.")
    say(
        state,
        "Create your identity and verify your email there. When the page shows your "
        "new account, run `coho login`.",
    )


# -- configure / profile -------------------------------------------------------------


def configure(
    ctx: typer.Context,
    profile_name: Annotated[
        str | None,
        typer.Option(
            "--profile",
            "-p",
            help="The profile to create or update. The same as the global --profile, "
            "which goes before the command name.",
        ),
    ] = None,
    url: Annotated[
        str | None,
        typer.Option("--url", help=f"The BFF base URL. New profiles: {PRODUCTION_URL}"),
    ] = None,
    oidc_domain: Annotated[
        str | None,
        typer.Option(
            "--oidc-domain",
            help=f"Coho's sign-in service. New profiles: {PRODUCTION_OIDC_DOMAIN}",
        ),
    ] = None,
    client_id: Annotated[
        str | None,
        typer.Option("--client-id", help="The CLI's client at the sign-in service: coho-cli."),
    ] = None,
    scopes: Annotated[
        str | None,
        typer.Option("--scopes", help=f"Space-separated. Default: {' '.join(DEFAULT_SCOPES)}"),
    ] = None,
    callback_port: Annotated[
        int | None,
        typer.Option(
            "--callback-port",
            help="Loopback port for the sign-in callback; the sign-in service accepts any.",
        ),
    ] = None,
    token_store: Annotated[
        str | None, typer.Option("--token-store", help="`keyring` (default) or `file`.")
    ] = None,
    make_current: Annotated[
        bool, typer.Option("--use/--no-use", help="Make it the current profile.")
    ] = True,
) -> None:
    """Create or update a profile (`--profile NAME`, default `default`)."""
    state = get_state(ctx)
    if profile_name:
        state.profile_name = profile_name
    existing = set(state.config.profiles)
    profile = state.config.profile(state.profile_name, create=True)
    # A profile being created points at production; one that already exists is only ever
    # changed by the flags below, so a profile aimed at dev stays aimed at dev.
    if profile.name not in existing:
        point_at_production(profile)
    if url:
        profile.url = url.rstrip("/")
    if oidc_domain:
        profile.oidc_domain = oidc_domain
    if client_id:
        profile.client_id = client_id
    if scopes:
        profile.scopes = scopes.split()
    if callback_port is not None:
        profile.callback_port = callback_port
    if token_store:
        if token_store not in ("keyring", "file"):
            raise Usage("--token-store must be `keyring` or `file`")
        profile.token_store = token_store
    if make_current or not state.config.current_profile:
        state.config.current_profile = profile.name
    state.save()
    say(state, f"Profile [bold]{profile.name}[/bold] saved to {state.config.path}.")
    _show_profile(state, profile)


profile_app = typer.Typer(
    help="Named environments: BFF URL, identity provider, saved context.", no_args_is_help=True
)


@profile_app.command("list")
def profile_list(ctx: typer.Context) -> None:
    """Every profile in the config file."""
    state = get_state(ctx)
    cfg = state.config
    table(
        state,
        {
            "current": cfg.current_profile,
            "profiles": {n: p.to_dict() for n, p in cfg.profiles.items()},
        },
        ["", "PROFILE", "URL", "LOGIN", "ACCOUNT", "PROJECT", "REF"],
        [
            (
                "*" if n == cfg.current_profile else "",
                n,
                p.url or "-",
                "pkce" if p.can_login else "token",
                p.context.account,
                p.context.project,
                p.context.ref,
            )
            for n, p in cfg.profiles.items()
        ],
        empty=(
            f"(no profiles saved; `default` points at {PRODUCTION_URL}. "
            f"`coho configure` writes one) — {cfg.path}"
        ),
    )


@profile_app.command("show")
def profile_show(ctx: typer.Context, name: Annotated[str | None, typer.Argument()] = None) -> None:
    """One profile's settings."""
    state = get_state(ctx)
    if name:
        if name not in state.config.profiles:
            raise Usage(f"no profile named '{name}'")
        profile = state.config.profiles[name]
    else:
        # Through `state.profile`, which resolves the current profile and, on a machine
        # with no config at all, answers with the production default.
        profile = state.profile
    _show_profile(state, profile)


@profile_app.command("use")
def profile_use(ctx: typer.Context, name: Annotated[str, typer.Argument()]) -> None:
    """Make a profile the current one."""
    state = get_state(ctx)
    if name not in state.config.profiles:
        raise Usage(f"no profile named '{name}'")
    state.config.current_profile = name
    state.save()
    say(state, f"Current profile is now [bold]{name}[/bold].")


@profile_app.command("delete")
def profile_delete(ctx: typer.Context, name: Annotated[str, typer.Argument()]) -> None:
    """Remove a profile and its stored tokens."""
    state = get_state(ctx)
    profile = state.config.profiles.pop(name, None)
    if profile is None:
        raise Usage(f"no profile named '{name}'")
    try:
        sdk_auth.token_store_for(profile).delete(name)
    except Exception as exc:  # noqa: BLE001 - best effort
        warn(f"could not remove stored tokens: {exc}")
    if state.config.current_profile == name:
        state.config.current_profile = next(iter(state.config.profiles), None)
    state.save()
    say(state, f"Deleted profile [bold]{name}[/bold].")


def _show_profile(state: State, profile: Profile) -> None:
    record(
        state,
        profile.to_dict() | {"name": profile.name},
        [
            ("profile", profile.name),
            ("url", profile.url or None),
            ("oidc_domain", profile.oidc_domain),
            ("client_id", profile.client_id),
            ("scopes", " ".join(profile.scopes)),
            ("callback_port", profile.callback_port),
            ("token_store", profile.token_store),
            ("account", profile.context.account),
            ("project", profile.context.project),
            ("ref", profile.context.ref),
        ],
    )
