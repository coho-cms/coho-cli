"""login, logout, whoami, signup, configure, profile."""

from __future__ import annotations

from typing import Annotated

import typer
from coho_management_sdk import auth as sdk_auth
from coho_management_sdk.errors import NotLoggedIn
from coho_management_sdk.profiles import DEFAULT_SCOPES, Profile

from .._output import console, record, say, table, warn
from .._state import State, Usage, get_state


def login(
    ctx: typer.Context,
    token: Annotated[
        str | None,
        typer.Option(
            "--token", help="Store this bearer token instead of running the browser flow."
        ),
    ] = None,
    no_browser: Annotated[
        bool, typer.Option("--no-browser", help="Print the URL instead of opening it.")
    ] = False,
    port: Annotated[
        int | None,
        typer.Option("--port", help="Loopback port for the callback (default: the profile's)."),
    ] = None,
    timeout: Annotated[
        int, typer.Option("--timeout", help="Seconds to wait for the browser.")
    ] = 300,
) -> None:
    """Sign in to the current profile.

    Opens the identity provider in a browser (PKCE, no client secret) and stores the
    tokens in the OS keyring, or a 0600 file when there is none. With `--token`, stores
    the given access token as-is — for a token obtained elsewhere.
    """
    state = get_state(ctx)
    profile = state.profile
    store = sdk_auth.token_store_for(profile)
    if token:
        store.save(profile.name, sdk_auth.TokenSet(access_token=token))
        say(state, f"Stored a token for profile [bold]{profile.name}[/bold].")
    else:
        if not profile.can_login:
            raise Usage(
                f"profile '{profile.name}' has no identity provider configured. Either\n"
                f"  coho configure --profile {profile.name} --oidc-domain https://… --client-id …\n"
                "or store a token you obtained elsewhere with `coho login --token …`."
            )

        def on_url(url: str) -> None:
            if no_browser:
                console.print("Open this URL in a browser to sign in:\n", highlight=False)
                console.print(url, highlight=False, markup=False)
            else:
                console.print(
                    "Opening your browser to sign in… (use --no-browser to print the URL instead)"
                )

        tokens = sdk_auth.login(
            profile,
            open_browser=(lambda _u: None) if no_browser else None,
            timeout=timeout,
            port=port,
            on_url=on_url,
        )
        store.save(profile.name, tokens)
        say(state, f"Signed in to profile [bold]{profile.name}[/bold].")
    # Confirm the token works, and show who we are.
    _print_me(state)


def logout(ctx: typer.Context) -> None:
    """Forget the stored tokens for the current profile."""
    state = get_state(ctx)
    sdk_auth.token_store_for(state.profile).delete(state.profile.name)
    say(state, f"Logged out of profile [bold]{state.profile.name}[/bold].")


def whoami(ctx: typer.Context) -> None:
    """Who is signed in, and which accounts they belong to."""
    _print_me(get_state(ctx))


def _print_me(state: State) -> None:
    try:
        me = state.coho.me()
    except NotLoggedIn:
        raise Usage(f"not logged in to profile '{state.profile.name}'. Run `coho login`.") from None
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
    """Found a new account. Finishes in the browser; then run `coho login`."""
    import webbrowser

    state = get_state(ctx)
    url = state.coho.signup_start(account_name, display_name=display_name)
    if no_browser:
        console.print(url, markup=False, highlight=False)
    else:
        webbrowser.open(url)
        say(state, "Opened the sign-up page. When it says you are signed in, run `coho login`.")


# -- configure / profile -------------------------------------------------------------


def configure(
    ctx: typer.Context,
    url: Annotated[str | None, typer.Option("--url", help="The BFF base URL.")] = None,
    oidc_domain: Annotated[
        str | None,
        typer.Option(
            "--oidc-domain",
            help="Cognito hosted-UI domain, e.g. https://x.auth.us-east-1.amazoncognito.com",
        ),
    ] = None,
    client_id: Annotated[
        str | None, typer.Option("--client-id", help="The CLI's public app client id.")
    ] = None,
    scopes: Annotated[
        str | None,
        typer.Option("--scopes", help=f"Space-separated. Default: {' '.join(DEFAULT_SCOPES)}"),
    ] = None,
    callback_port: Annotated[
        int | None,
        typer.Option("--callback-port", help="Loopback port registered on the app client."),
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
    profile = state.config.profile(state.profile_name, create=True)
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
        empty=f"(no profiles; create one with `coho configure --url …`) — {cfg.path}",
    )


@profile_app.command("show")
def profile_show(ctx: typer.Context, name: Annotated[str | None, typer.Argument()] = None) -> None:
    """One profile's settings."""
    state = get_state(ctx)
    profile = state.config.profile(name or state.profile_name)
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
