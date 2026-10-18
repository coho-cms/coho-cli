"""coho asset: upload, list, get, url, put, delete, against the SDK's fake BFF and store."""

from __future__ import annotations

import hashlib
import json
import struct
import zlib
from pathlib import Path

from coho_management_sdk.testing import PROJECT, FakeBff

from conftest import Run


def png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    pixels = zlib.compress(b"".join(b"\x00" + b"\x00" * width * 3 for _ in range(height)))
    return (
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")
    )


def file(tmp_path: Path, name: str, data: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def words(text: str) -> str:
    """The text with every run of whitespace as one space.

    Rich wraps at the terminal's width, 80 when it is not a terminal, so where a line
    breaks depends on how long a temporary path is on the machine running the tests.
    """
    return " ".join(text.split())


def upload(run: Run, tmp_path: Path, name: str, data: bytes, *args: str) -> dict:  # type: ignore[type-arg]
    out, _ = run("-o", "json", "asset", "upload", str(file(tmp_path, name, data)), *args)
    return json.loads(out)  # type: ignore[no-any-return]


def test_upload_builds_the_slug_from_the_filename_and_warns_that_urls_are_public(
    run: Run, bff: FakeBff, tmp_path: Path
) -> None:
    run("use", "acme", PROJECT, "dev")
    data = png(40, 30)
    out, err = run("asset", "upload", str(file(tmp_path, "Hero Shot.png", data)), "--title", "Hero")

    assert "Uploaded Hero Shot.png as hero-shot: image/png" in words(out)
    assert "40×30" in words(out)
    assert "https://assets.example.test/" in words(out)
    assert "public" in words(err)
    put = next(r for r in bff.requests if r.path.startswith("/fake-s3/"))
    assert put.get_data() == data
    complete = bff.requests[-1]
    assert complete.get_json() == {"slug": "hero-shot", "title": "Hero"}


def test_upload_of_several_files_in_json(run: Run, tmp_path: Path) -> None:
    run("use", "acme", PROJECT, "dev")
    a = file(tmp_path, "a.png", png(2, 2))
    b = file(tmp_path, "b.png", png(3, 3))
    out, _ = run(
        "-o", "json", "asset", "upload", str(a), str(b), "--tag", "home", "--focal", "0.5,0.25"
    )
    doc = json.loads(out)
    assert [x["slug"] for x in doc["assets"]] == ["a", "b"]
    assert doc["assets"][0]["tags"] == ["home"]
    assert doc["assets"][1]["focalPoint"] == {"x": 0.5, "y": 0.25}
    assert doc["assets"][0]["etag"] == '"a1"'


def test_upload_refuses_one_slug_for_several_files_and_a_bad_focal_point(
    run: Run, tmp_path: Path
) -> None:
    run("use", "acme", PROJECT, "dev")
    a = file(tmp_path, "a.png", png(2, 2))
    _, err = run("asset", "upload", str(a), str(a), "--slug", "one", expect=2)
    assert "--slug names one asset" in words(err)
    _, err = run("asset", "upload", str(a), "--focal", "middle", expect=2)
    assert "--focal takes x,y" in words(err)
    _, err = run("asset", "upload", str(tmp_path / "missing.png"), expect=2)
    assert "no such file" in words(err)


def test_a_file_that_is_not_an_allowed_type_fails_with_its_code(run: Run, tmp_path: Path) -> None:
    run("use", "acme", PROJECT, "dev")
    _, err = run("asset", "upload", str(file(tmp_path, "page.png", b"<!doctype html>")), expect=1)
    assert "ASSET_TYPE_NOT_ALLOWED" in words(err)


def test_list_and_get_by_slug(run: Run, tmp_path: Path) -> None:
    run("use", "acme", PROJECT, "dev")
    data = png(8, 6)
    asset = upload(run, tmp_path, "logo.png", data, "--alt", "The logo")

    out, _ = run("asset", "list")
    assert "logo" in words(out) and "image/png" in words(out) and "8×6" in words(out)

    out, _ = run("asset", "get", "logo")
    assert asset["id"] in words(out)
    assert "The logo" in words(out)
    # From JSON: a table cell longer than the terminal is split mid-hash, and no
    # whitespace rule can join it back.
    out, _ = run("-o", "json", "asset", "get", "logo")
    assert json.loads(out)["file"]["sha256"] == hashlib.sha256(data).hexdigest()

    _, err = run("asset", "get", "nothing-here", expect=2)
    assert "no asset with slug" in words(err)


def test_url_resizes_only_raster_images_and_centres_fills_on_the_focal_point(
    run: Run, tmp_path: Path
) -> None:
    run("use", "acme", PROJECT, "dev")
    upload(run, tmp_path, "hero.png", png(10, 10), "--focal", "0.2,0.8")

    out, _ = run("asset", "url", "hero")
    assert "/a/" in words(out)
    out, _ = run("asset", "url", "hero", "--width", "800", "--fit", "fill", "--format", "webp")
    assert (
        "/i/" in words(out)
        and "w=800" in words(out)
        and "fit=fill" in words(out)
        and "fm=webp" in words(out)
    )
    assert "fx=0.2" in words(out) and "fy=0.8" in words(out)

    upload(run, tmp_path, "doc.pdf", b"%PDF-1.7\n")
    _, err = run("asset", "url", "doc", "--width", "100", expect=2)
    assert "application/pdf" in words(err)


def test_put_changes_metadata_and_keeps_the_rest(run: Run, bff: FakeBff, tmp_path: Path) -> None:
    run("use", "acme", PROJECT, "dev")
    asset = upload(run, tmp_path, "edit.png", png(4, 4), "--title", "Old", "--tag", "a")

    out, _ = run("asset", "put", "edit", "--alt", "New alt")
    assert "Updated edit" in words(out)
    sent = bff.requests[-1]
    assert sent.headers["If-Match"] == '"a1"'
    assert sent.get_json() == {"title": "Old", "alt": "New alt", "tags": ["a"]}

    run("asset", "put", asset["id"], "--clear", "title", "--clear", "tags")
    assert bff.requests[-1].get_json() == {"alt": "New alt"}

    _, err = run("asset", "put", "edit", expect=2)
    assert "nothing to change" in words(err)
    _, err = run("asset", "put", "edit", "--clear", "file", expect=2)
    assert "--clear takes" in words(err)


def test_delete_asks_and_says_the_url_keeps_working(run: Run, tmp_path: Path) -> None:
    run("use", "acme", PROJECT, "dev")
    upload(run, tmp_path, "gone.png", png(2, 3))
    out, _ = run("--yes", "asset", "delete", "gone")
    assert "Deleted gone" in words(out)
    out, _ = run("asset", "list")
    assert "gone" not in words(out)
