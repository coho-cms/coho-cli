from __future__ import annotations

import json
from pathlib import Path

import pytest
from coho_management_sdk import testing
from coho_management_sdk.profiles import Config
from coho_management_sdk.testing import ACCOUNT, ENTRY, INVITATION_TOKEN, ME, PROJECT, FakeBff

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


def test_entry_set_is_read_modify_write(run: Run, bff: FakeBff) -> None:
    run("use", "acme", PROJECT, "dev")
    out, _ = run(
        "-o", "json", "entry", "put", ENTRY, "--set", "title.en-US=Changed", "--set", "rank=7"
    )
    body = json.loads(out)
    assert body["fields"] == {"title": {"en-US": "Changed"}, "rank": 7}
    assert body["etag"] == '"v2"'
    assert bff.last().headers["If-Match"] == '"v1"'


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
    assert "no account for this identity" in text and "coho signup" in text
    assert "UNAUTHENTICATED" not in text


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
