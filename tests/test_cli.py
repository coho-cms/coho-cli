from __future__ import annotations

import json
from pathlib import Path

import pytest
from coho_management_sdk import testing
from coho_management_sdk.profiles import Config
from coho_management_sdk.testing import (
    ACCOUNT,
    ENTRY,
    INVALID_ENTRIES_SHOWN,
    INVITATION_TOKEN,
    ME,
    PROJECT,
    FakeBff,
)

from coho_cli import __version__
from conftest import Run


def test_version(run: Run) -> None:
    out, _ = run("--version")
    lines = [line.strip() for line in out.splitlines()]
    assert lines[0] == "CohoCMS"
    assert lines[1] == f"a CohoWorks project · v{__version__}"
    assert lines[2].startswith("coho-management-sdk ")


def test_status_without_context_hints(run: Run) -> None:
    out, _ = run("status")
    assert "profile" in out and "coho use" in out


def test_use_verifies_and_saves_context(run: Run, home: Path) -> None:
    out, _ = run("use", "acme", PROJECT, "dev")
    cfg = Config.load(home / "config.toml").profile("test")
    assert (
        cfg.context.account == ACCOUNT
        and cfg.context.project == PROJECT
        and cfg.context.ref == "dev"
    )
    assert cfg.project_name(ACCOUNT, PROJECT) == "Marketing site"
    # The registry makes the name usable afterwards.
    run("use", "acme", "Marketing site", "feature/pricing")
    assert Config.load(home / "config.toml").profile("test").context.ref == "feature/pricing"


def test_use_unknown_ref_is_not_found_exit_5(run: Run) -> None:
    _, err = run("use", "acme", PROJECT, "nope", expect=5)
    assert "REF_NOT_FOUND" in err


def test_branch_create_makes_the_branch_the_current_ref(run: Run, home: Path) -> None:
    run("use", "acme", PROJECT, "dev")
    out, err = run("branch", "create", "feature/spring")
    assert "Context ref is now feature/spring" in out and "warning" not in err
    assert Config.load(home / "config.toml").profile("test").context.ref == "feature/spring"
    out, _ = run("status")
    assert "feature/spring" in out


def test_branch_create_no_use_keeps_the_current_ref(run: Run, home: Path) -> None:
    run("use", "acme", PROJECT, "dev")
    out, _ = run("branch", "create", "feature/spring", "--no-use")
    assert "Context ref" not in out
    assert Config.load(home / "config.toml").profile("test").context.ref == "dev"


def test_branch_create_warns_when_coho_ref_hides_the_switch(
    run: Run, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run("use", "acme", PROJECT, "dev")
    monkeypatch.setenv("COHO_REF", "dev")
    _, err = run("branch", "create", "feature/spring")
    assert "COHO_REF=dev overrides the saved ref, so commands still use dev" in err
    assert Config.load(home / "config.toml").profile("test").context.ref == "feature/spring"


def test_branch_create_warns_when_ref_flag_hides_the_switch(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")
    _, err = run("--ref", "dev", "branch", "create", "feature/spring")
    assert "--ref dev overrides the saved ref" in err


def test_ref_switch_makes_the_ref_current(run: Run, home: Path) -> None:
    run("use", "acme", PROJECT, "dev")
    out, err = run("ref", "switch", "feature/pricing")
    assert "Context ref is now feature/pricing" in out and "warning" not in err
    cfg = Config.load(home / "config.toml").profile("test")
    assert (cfg.context.account, cfg.context.project) == (ACCOUNT, PROJECT)
    assert cfg.context.ref == "feature/pricing"
    out, _ = run("status")
    assert "feature/pricing" in out


def test_ref_switch_to_an_unknown_ref_is_not_found_and_keeps_the_ref(run: Run, home: Path) -> None:
    run("use", "acme", PROJECT, "dev")
    _, err = run("ref", "switch", "nope", expect=5)
    assert "REF_NOT_FOUND" in err
    assert Config.load(home / "config.toml").profile("test").context.ref == "dev"


def test_ref_switch_needs_a_project(run: Run) -> None:
    _, err = run("ref", "switch", "dev", expect=2)
    assert "coho use" in err


def test_ref_switch_warns_when_coho_ref_hides_the_switch(
    run: Run, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run("use", "acme", PROJECT, "dev")
    monkeypatch.setenv("COHO_REF", "dev")
    _, err = run("ref", "switch", "feature/pricing")
    assert "COHO_REF=dev overrides the saved ref, so commands still use dev" in err
    assert Config.load(home / "config.toml").profile("test").context.ref == "feature/pricing"


def test_ref_switch_json_is_the_ref(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")
    out, _ = run("-o", "json", "ref", "switch", "feature/pricing")
    assert json.loads(out)["name"] == "feature/pricing"


def test_missing_context_is_usage_error(run: Run) -> None:
    _, err = run("entry", "list", expect=2)
    assert "coho use" in err


def test_whoami_json_is_the_contract_body(run: Run) -> None:
    out, _ = run("-o", "json", "whoami")
    body = json.loads(out)
    assert body["user"]["email"] == "ada@acme.example"
    assert "externalId" not in json.dumps(body)


def test_the_only_account_is_used_when_none_is_chosen(run: Run) -> None:
    out, _ = run("project", "list")
    assert "no account" not in out.lower()


def test_with_several_accounts_one_must_be_chosen(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    second = {
        "accountId": "22222222-2222-4222-8222-000000000002",
        "accountName": "Beta",
        "role": "member",
    }
    monkeypatch.setitem(ME, "accounts", [*ME["accounts"], second])
    _, err = run("project", "list", expect=2)
    assert "2 accounts (Acme, Beta)" in err and "coho use" in err


def test_with_no_account_signup_or_an_invitation_is_suggested(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(ME, "accounts", [])
    _, err = run("project", "list", expect=2)
    assert "coho signup" in err


def test_project_list_shows_the_server_list_with_roles_and_local_leftovers(run: Run) -> None:
    run("project", "register", PROJECT, "Marketing site")
    out, _ = run("project", "list")
    assert "Marketing site" in out and "owner" in out and "local only" not in out

    # A remembered project the server no longer lists for you is shown, flagged.
    gone = "77777777-7777-4777-8777-777777777777"
    cfg = Config.load()
    cfg.profile("test").remember_project(ACCOUNT, "Old site", gone)
    cfg.save()
    out, _ = run("project", "list")
    assert "Old site" in out and "local only" in out

    data = json.loads(run("-o", "json", "project", "list")[0])
    assert {p["source"] for p in data["projects"]} == {"server", "local"}


def test_use_finds_a_project_by_its_server_name_without_any_local_memory(run: Run) -> None:
    run("use", "acme", "marketing site")
    out, _ = run("status")
    assert PROJECT in out


def test_status_shows_name_then_id_for_account_and_project(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")
    out, _ = run("status")
    assert f"account  Acme ({ACCOUNT})" in out
    assert f"project  Marketing site  ({PROJECT})" in out
    out, _ = run("-o", "json", "status")
    body = json.loads(out)
    assert body["accountName"] == "Acme" and body["projectName"] == "Marketing site"


def test_two_projects_with_one_name_must_be_chosen_by_id(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    twin = {
        "id": "88888888-8888-4888-8888-888888888888",
        "name": "Marketing site",
        "role": "author",
    }
    monkeypatch.setattr(testing, "PROJECTS", [*testing.PROJECTS, twin])
    _, err = run("use", "acme", "Marketing site", expect=2)
    assert "2 projects are named" in err and twin["id"] in err


def test_project_create_sets_context_and_registry(run: Run, home: Path) -> None:
    run("use", "acme")
    out, _ = run("project", "create", "Marketing site")
    assert "v0.0.x" in out
    cfg = Config.load(home / "config.toml").profile("test")
    assert cfg.context.project == PROJECT and cfg.context.ref == "v0.0.x"
    out, _ = run("project", "list")
    assert "Marketing site" in out and PROJECT in out


def test_entry_list_table_and_json(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")
    out, _ = run("entry", "list", "--limit", "2")
    assert "post-0" in out and "post-1" in out and "post-2" not in out and "--offset 2" in out
    out, _ = run("-o", "json", "entry", "list", "--all")
    assert len(json.loads(out)["entries"]) == 5


def test_preview_entries_reads_the_delivery_graph(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")
    out, _ = run("preview", "entries")
    assert ENTRY in out and "blogPost" in out and "hello" in out
    out, _ = run("-o", "json", "preview", "entries")
    assert json.loads(out)["roots"] == [ENTRY]
    assert "more:" not in out


def test_preview_entries_says_where_the_next_page_starts(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT, "dev")
    graph = {
        "roots": [ENTRY],
        "entries": {ENTRY: {"id": ENTRY, "type": "blogPost", "slug": "hello", "fields": {}}},
        "unresolved": {},
        "hasMore": True,
    }
    path = f"/api/v1/accounts/{ACCOUNT}/projects/{PROJECT}/preview/dev/entries"
    bff.server.expect_oneshot_request(path, method="GET").respond_with_json(graph)
    out, _ = run("preview", "entries", "--limit", "1", "--offset", "3")
    assert "more: --offset 4" in out
    bff.server.expect_oneshot_request(path, method="GET").respond_with_json(graph)
    out, _ = run("-o", "json", "preview", "entries", "--limit", "1")
    assert json.loads(out)["hasMore"] is True


def test_entry_set_is_read_modify_write(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT, "dev")
    out, _ = run(
        "-o", "json", "entry", "put", ENTRY, "--set", "title.en-US=Changed", "--set", "rank=7"
    )
    body = json.loads(out)
    assert body["fields"] == {"title": {"en-US": "Changed"}, "rank": 7}
    assert body["etag"] == '"v2"'
    assert bff.last().headers["If-Match"] == '"v1"'


def test_entry_set_takes_a_repeater_as_a_json_list(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT, "dev")
    items = '[{"authors": "ASCE", "year": 2022, "title": "Minimum design loads"}]'
    out, _ = run("-o", "json", "entry", "put", ENTRY, "--set", f"citations={items}")
    # Sent as a list of objects, not a string; the server stamps each item's _id and _type.
    assert json.loads(out)["fields"]["citations"] == json.loads(items)


def test_type_list_says_which_types_are_components(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT, "dev")
    path = f"/api/v1/accounts/{ACCOUNT}/projects/{PROJECT}/refs/dev/types"
    citation = {"_name": "Citation", "kind": "component", "fields": [{"id": "authors"}]}
    bff.server.expect_oneshot_request(path, method="GET").respond_with_json(
        {
            "types": [
                {"slug": "blogPost", "version": "t1", "definition": {"_name": "B", "fields": []}},
                {"slug": "citation", "version": "c1", "kind": "component", "definition": citation},
            ]
        }
    )
    out, _ = run("type", "list")
    assert "KIND" in out
    rows = {
        line.split()[0]: line.split()[1] for line in out.splitlines() if line.strip()[:1].islower()
    }
    assert rows == {"blogPost": "content", "citation": "component"}


def test_entry_put_file_needs_precondition(run: Run, tmp_path: Path) -> None:
    run("use", "acme", PROJECT, "dev")
    f = tmp_path / "fields.json"
    f.write_text(json.dumps({"title": {"en-US": "x"}}))
    _, err = run("entry", "put", ENTRY, "--file", str(f), expect=4)
    assert "PRECONDITION_REQUIRED" in err and "--force" in err
    out, _ = run("-o", "json", "entry", "put", ENTRY, "--file", str(f), "--force")
    assert json.loads(out)["fields"] == {"title": {"en-US": "x"}}


def test_entry_create_inline_and_validation_error(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")
    out, _ = run(
        "-o",
        "json",
        "entry",
        "create",
        "-t",
        "blogPost",
        "-s",
        "hello",
        "-f",
        '{"title": {"en-US": "Hi"}}',
    )
    assert json.loads(out)["slug"] == "hello"
    _, err = run("entry", "create", "-t", "blogPost", "-s", "hello", "--set", "rank=1", expect=1)
    assert "VALIDATION_FAILED" in err and "title: required" in err


def test_type_put_refuses_blind_update(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")
    _, err = run("type", "put", "blogPost", "-f", '{"_name":"B","fields":[]}', expect=2)
    assert "--if-match" in err
    out, _ = run(
        "-o",
        "json",
        "type",
        "put",
        "blogPost",
        "-f",
        '{"_name":"B","fields":[]}',
        "--if-match",
        '"t1"',
    )
    assert json.loads(out)["etag"] == '"t2"'
    out, _ = run(
        "-o", "json", "type", "put", "newType", "-f", '{"definition": {"_name":"N","fields":[]}}'
    )
    assert json.loads(out)["slug"] == "newType"


def test_diff_and_merge_conflict_exit_4(run: Run, tmp_path: Path) -> None:
    run("use", "acme", PROJECT, "feature/pricing")
    out, _ = run("diff", "v0.0.x")
    assert "conflicts" in out and "title.en-US" in out
    _, err = run("merge", "--into", "v0.0.x", expect=4)
    assert "MERGE_CONFLICT" in err and "pricing: field at title.en-US" in err
    res = tmp_path / "res.json"
    res.write_text(json.dumps([{"nodeId": ENTRY, "path": "title.en-US", "take": "source"}]))
    out, _ = run("-o", "json", "merge", "--into", "v0.0.x", "--resolve", str(res), "--reviewed")
    assert json.loads(out)["resolved"] == 1


# What a tag cut with --validate finds wrong, worded as the server words it: the schema
# validator's messages start with their path, a pattern holds brackets, and one entry's
# type is gone from the ref.
INVALID_ENTRIES = [
    {
        "id": "66666666-6666-4666-8666-000000000001",
        "slug": "about-us",
        "type": "page",
        "errors": [{"path": "$", "message": "$: required property 'layout' not found"}],
    },
    {
        "id": "66666666-6666-4666-8666-000000000002",
        "slug": "pricing",
        "type": "page",
        "errors": [
            {"path": "$", "message": "$: required property 'layout' not found"},
            {"path": "$.code", "message": "$.code: does not match the regex pattern ^[a-z0-9-]+$"},
        ],
    },
    {
        "id": "66666666-6666-4666-8666-000000000003",
        "slug": "spring-banner",
        "errors": [{"path": "/", "message": "its content type is not on this ref"}],
    },
]


def test_tag_create_sends_validate_only_with_the_flag(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT)
    run("tag", "create", "v1.1.0", "--branch", "v0.0.x")
    assert bff.last().get_json() == {"name": "v1.1.0", "ref": "v0.0.x"}
    out, _ = run("tag", "create", "v1.1.0", "--branch", "v0.0.x", "--validate")
    assert bff.last().get_json() == {"name": "v1.1.0", "ref": "v0.0.x", "validate": True}
    assert "v1.1.0" in out  # valid content is tagged as usual


def test_tag_create_validate_lists_each_invalid_entry_and_exits_1(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT)
    bff.invalid_entries = INVALID_ENTRIES
    out, err = run("tag", "create", "v1.1.0", "--branch", "v0.0.x", "--validate", expect=1)
    assert out == ""
    lines = err.splitlines()
    assert lines[0].startswith("error TAG_CONTENT_INVALID:")
    summary = lines[lines.index("3 invalid entries:") + 1 :]
    assert summary == [
        "  about-us (page) 66666666-6666-4666-8666-000000000001",
        "    $: required property 'layout' not found",
        "  pricing (page) 66666666-6666-4666-8666-000000000002",
        "    $: required property 'layout' not found",
        "    $.code: does not match the regex pattern ^[a-z0-9-]+$",
        "  spring-banner (no type) 66666666-6666-4666-8666-000000000003",
        "    /: its content type is not on this ref",
    ]


def test_tag_create_validate_says_how_many_entries_are_not_listed(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT)
    bff.invalid_entries = [
        {"id": f"id-{i}", "slug": f"post-{i:03}", "type": "blogPost", "errors": []}
        for i in range(INVALID_ENTRIES_SHOWN + 3)
    ]
    _, err = run("tag", "create", "v1.1.0", "--branch", "v0.0.x", "--validate", expect=1)
    text = " ".join(err.split())  # the terminal wraps long lines; compare the words
    assert "103 invalid entries:" in text and "post-099" in text and "post-100" not in text
    assert "Listed the first 100 of 103, by slug." in text


def test_tag_create_validate_prints_the_problem_with_output_json(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT)
    bff.invalid_entries = INVALID_ENTRIES
    out, err = run(
        "-o", "json", "tag", "create", "v1.1.0", "--branch", "v0.0.x", "--validate", expect=1
    )
    problem = json.loads(out)
    assert problem["code"] == "TAG_CONTENT_INVALID" and problem["entryCount"] == 3
    assert [e["slug"] for e in problem["invalidEntries"]] == [
        "about-us",
        "pricing",
        "spring-banner",
    ]
    assert err == ""


def test_promote_and_rollback(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT)
    bff.snapshot_not_ready_times = 1
    out, _ = run("-o", "json", "promote", "prod", "v1.1.0", "-m", "ship it")
    assert json.loads(out)["target"] == "v1.1.0"
    _, err = run("promote", "prod", "v9.0.0")
    assert "SKIPPED_TIER" in err
    out, _ = run("-y", "-o", "json", "rollback", "prod")
    assert json.loads(out)["target"] == "v0.9.0"
    _, err = run("promote", "prod", "v1.1.0", "--expected", "wrong", expect=4)
    assert "ENVIRONMENT_MOVED" in err


def test_key_create_prints_secret_once(run: Run) -> None:
    run("use", "acme", PROJECT)
    out, err = run("key", "create", "--label", "site", "--ref", "prod")
    assert "coho_dk_SECRET" in out and "shown once" in err
    out, _ = run("-o", "json", "key", "create")
    assert json.loads(out)["key"] == "coho_dk_SECRET"


def test_invite_prints_link_with_fragment(run: Run, bff: FakeBff) -> None:
    run("use", "acme")
    out, err = run("invite", "create", "jane@acme.example")
    assert f"{bff.url}/invite#secret-invitation-token" in out and "shown once" in err
    _, err = run("invite", "create", "jane@acme.example", "--role", "boss", expect=2)
    assert "--role" in err


def test_member_role_last_admin(run: Run) -> None:
    run("use", "acme")
    _, err = run("member", "role", "ada@acme.example", "member", expect=1)
    assert "LAST_ADMIN" in err


def test_role_grant_me(run: Run) -> None:
    run("use", "acme", PROJECT)
    out, _ = run("-o", "json", "role", "grant", "me", "maintainer")
    assert json.loads(out)["role"] == "maintainer"


def test_export_branch(run: Run, tmp_path: Path) -> None:
    run("use", "acme", PROJECT, "feature/pricing")
    out, _ = run("export", "--out", str(tmp_path / "e.ndjson"))
    assert "42" in out and (tmp_path / "e.ndjson").exists()


def test_not_logged_in_exit_3(run: Run, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("COHO_ACCESS_TOKEN")
    _, err = run("account", "list", expect=3)
    assert "coho login" in err


def test_login_with_token_stores_and_verifies(run: Run, home: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("COHO_ACCESS_TOKEN")
    out, _ = run("login", "--token", "test-token")
    assert "ada@acme.example" in out
    assert (home / "credentials.json").exists()
    run("logout")
    _, err = run("whoami", expect=2)
    assert "not logged in" in err.lower()


def test_configure_creates_profile(run: Run, home: Path) -> None:
    out, _ = run(
        "-p",
        "staging",
        "configure",
        "--url",
        "https://staging.example/",
        "--oidc-domain",
        "idp",
        "--client-id",
        "cid",
    )
    cfg = Config.load(home / "config.toml")
    assert (
        cfg.current_profile == "staging" and cfg.profile("staging").url == "https://staging.example"
    )
    out, _ = run("profile", "list")
    assert "staging" in out and "pkce" in out


def test_configure_takes_profile_after_its_name_as_its_help_says(run: Run, home: Path) -> None:
    run("configure", "--profile", "dev", "--url", "https://api-dev.example", "--client-id", "x")
    cfg = Config.load(home / "config.toml")
    assert cfg.profile("dev").url == "https://api-dev.example"
    assert cfg.profile("dev").client_id == "x"


# -- before a login: what a person does before they have one ---------------------------


def test_signup_opens_a_page_with_no_login_and_no_request(
    run: Run, bff: FakeBff, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("COHO_ACCESS_TOKEN")
    before = len(bff.requests)
    out, _ = run("signup", "Maya Co", "--name", "Maya", "--no-browser")
    assert f"{bff.url}/auth/signup?accountName=Maya%20Co" in out
    assert "returnTo=%2Fapi%2Fv1%2Fme" in out and "displayName=Maya" in out
    assert len(bff.requests) == before  # the CLI called nothing; the browser does it all


def test_signup_refuses_a_blank_name(run: Run, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COHO_ACCESS_TOKEN")
    _, err = run("signup", "   ", "--no-browser", expect=2)
    assert "blank" in err


def test_invite_lookup_needs_no_login(
    run: Run, bff: FakeBff, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("COHO_ACCESS_TOKEN")
    out, _ = run("invite", "lookup", f"https://example/invite#{INVITATION_TOKEN}")
    assert "Acme" in out and "pending" in out
    assert "Authorization" not in bff.last().headers


def test_an_error_names_its_code_once(run: Run, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COHO_ACCESS_TOKEN")
    _, err = run("account", "list", expect=3)
    assert err.count("NOT_LOGGED_IN") == 1


def test_login_explains_an_identity_with_no_coho_account(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The provider issued a valid token, but the auth service knows no account for
    it: say that, rather than a bare UNAUTHENTICATED straight after "Signed in"."""
    monkeypatch.delenv("COHO_ACCESS_TOKEN")
    _, err = run("login", "--token", "valid-but-unknown-identity", expect=2)
    text = " ".join(err.split())  # the terminal wraps long lines; compare the words
    assert "no account for this identity" in text and "/auth/login" in text
    assert "UNAUTHENTICATED" not in text


def _signs_in_as(monkeypatch: pytest.MonkeyPatch, run: Run, token: str) -> None:
    """The browser sign-in, faked: the profile can log in, and the provider hands back [token]."""
    from coho_management_sdk import auth as sdk_auth

    import coho_cli.commands.auth as cli_auth

    monkeypatch.delenv("COHO_ACCESS_TOKEN")
    run(
        "configure",
        "--profile",
        "test",
        "--oidc-domain",
        "https://auth.example",
        "--client-id",
        "coho-cli",
    )
    monkeypatch.setattr(sdk_auth, "login", lambda *a, **k: sdk_auth.TokenSet(access_token=token))
    monkeypatch.setattr(cli_auth, "ACCOUNT_POLL_SECONDS", 0.01)


def test_login_with_no_organization_finishes_in_the_browser_and_waits_for_it(
    run: Run, bff: FakeBff, monkeypatch: pytest.MonkeyPatch
) -> None:
    """UL-19: the CLI's sign-in never passes the BFF, so it sends the person to the BFF's
    sign-in, which asks for the organization, and waits until the account exists."""
    _signs_in_as(monkeypatch, run, "fresh-token")
    opened: list[str] = []

    def finish_in_browser(url: str) -> bool:
        opened.append(url)
        bff.tokens.add("fresh-token")  # the person named their organization
        return True

    monkeypatch.setattr("webbrowser.open", finish_in_browser)
    out, _ = run("login")

    assert opened == [f"{bff.url}/auth/login?returnTo=%2Fapi%2Fv1%2Fme"]
    text = " ".join(out.split())
    assert "Finish setting up in your browser" in text
    assert "ada@acme.example" in text  # and then who we are, as any login shows


def test_login_that_is_never_finished_stops_waiting_and_says_what_next(
    run: Run, bff: FakeBff, monkeypatch: pytest.MonkeyPatch
) -> None:
    _signs_in_as(monkeypatch, run, "never-finished")
    out, err = run("login", "--no-browser", "--timeout", "0", expect=2)
    assert f"{bff.url}/auth/login?returnTo=%2Fapi%2Fv1%2Fme" in out
    assert "coho whoami" in " ".join(err.split())


def _save_account(home: Path, account: str) -> None:
    from coho_management_sdk.profiles import Config

    cfg = Config.load(home / "config.toml")
    cfg.profile("test").context.account = account
    cfg.save()


def test_a_saved_account_that_is_gone_gives_way_to_the_only_one(run: Run, home: Path) -> None:
    """A context saved before the environment was reset names an account that no longer
    exists. Someone with one account gets that one, saved in its place, and is told once."""
    from coho_management_sdk.profiles import Config
    from coho_management_sdk.testing import ACCOUNT, GONE_ACCOUNT

    _save_account(home, GONE_ACCOUNT)
    out, err = run("project", "list")
    assert "Marketing site" in out
    assert "your only account" in " ".join(err.split())

    saved = Config.load(home / "config.toml").profile("test").context
    assert saved.account == ACCOUNT and saved.project is None and saved.ref is None

    _, err = run("project", "list")
    assert "warning" not in err  # quiet from then on


def test_a_saved_account_that_is_gone_asks_which_when_there_are_several(
    run: Run, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coho_management_sdk import testing
    from coho_management_sdk.testing import GONE_ACCOUNT

    second = {
        "accountId": "44444444-4444-4444-8444-444444444444",
        "accountName": "Globex",
        "role": "member",
    }
    monkeypatch.setitem(testing.ME, "accounts", [*testing.ME["accounts"], second])
    _save_account(home, GONE_ACCOUNT)
    _, err = run("project", "list", expect=2)
    text = " ".join(err.split())
    assert "not one of yours" in text and "Acme, Globex" in text and "coho use <account>" in text


def test_an_account_named_in_the_environment_is_used_as_given_and_nothing_is_rewritten(
    run: Run, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coho_management_sdk.profiles import Config
    from coho_management_sdk.testing import GONE_ACCOUNT

    monkeypatch.setenv("COHO_ACCOUNT", GONE_ACCOUNT)
    _, err = run("project", "list", expect=5)
    assert "ACCOUNT_NOT_FOUND" in err and "saved with" not in err
    assert Config.load(home / "config.toml").profile("test").context.account is None


def test_an_account_named_on_the_command_line_gets_no_hint_about_the_saved_one(run: Run) -> None:
    from coho_management_sdk.testing import GONE_ACCOUNT

    _, err = run("--account", GONE_ACCOUNT, "project", "list", expect=5)
    assert "ACCOUNT_NOT_FOUND" in err and "saved with" not in err


def test_whoami_with_a_rejected_token_still_says_unauthenticated(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the moment right after signing in gets the friendlier reading."""
    monkeypatch.setenv("COHO_ACCESS_TOKEN", "some-rejected-token")
    _, err = run("whoami", expect=3)
    assert "UNAUTHENTICATED" in err


def test_token_create_list_and_revoke(run: Run) -> None:
    run("use", "acme", PROJECT)
    out, _ = run("token", "create", "--role", "maintainer", "--label", "CI")
    assert "coho_pt_SECRET" in out
    out, _ = run("token", "list")
    assert "tok-1" in out and "maintainer" in out and "active" in out
    run("--yes", "token", "revoke", "tok-1")


def test_a_token_cannot_be_created_as_owner(run: Run) -> None:
    run("use", "acme", PROJECT)
    _, err = run("token", "create", "--role", "owner", "--label", "CI", expect=2)
    assert "never be an owner" in err


def test_login_stores_a_project_token_without_asking_who_it_is(run: Run, bff: FakeBff) -> None:
    out, _ = run("login", "--token", "coho_pt_" + "a" * 43)
    assert "project token" in out
    assert not any(r.path == "/api/v1/me" for r in bff.requests)


def test_trait_list_names_the_types_that_take_each(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT, "dev")
    path = f"/api/v1/accounts/{ACCOUNT}/projects/{PROJECT}/refs/dev/types"
    page = {"_name": "Page", "traits": ["seo"], "fields": []}
    bff.server.expect_oneshot_request(path, method="GET").respond_with_json(
        {"types": [{"slug": "page", "version": "p1", "definition": page}]}
    )
    out, _ = run("trait", "list")
    assert "TAKEN BY" in out
    assert "seo" in out and "metaTitle" in out and "page" in out


def test_trait_put_and_a_refusal_that_says_how_far_it_reaches(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")
    required = '{"_name":"SEO","fields":[{"id":"metaTitle","type":"text","required":true}]}'
    _, err = run("trait", "put", "seo", "-f", required, expect=2)
    assert "--if-match" in err
    _, err = run("trait", "put", "seo", "-f", required, "--if-match", '"s1"', expect=1)
    assert "DESTRUCTIVE_SCHEMA_CHANGE" in err
    assert "reaches: blogPost, and 5 entries" in err
    out, _ = run(
        "-o",
        "json",
        "trait",
        "put",
        "seo",
        "-f",
        required,
        "--if-match",
        '"s1"',
        "--confirm-destructive",
    )
    assert '"s2"' in out


def test_a_trait_in_use_is_not_deleted(run: Run) -> None:
    run("use", "acme", PROJECT, "dev")
    _, err = run("-y", "trait", "delete", "seo", expect=1)
    assert "TRAIT_IN_USE" in err
    assert "reaches: blogPost" in err
    out, _ = run("-y", "trait", "delete", "unused")
    assert "Deleted trait unused." in out
