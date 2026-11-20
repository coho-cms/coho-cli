"""The Windows installer's identity and its winget manifests (packaging/windows)."""

from __future__ import annotations

import datetime
import uuid
from pathlib import Path

import pytest
from msi_version import UPGRADE_CODE, guid, msi_identity
from winget_manifest import manifest_folder, manifests


@pytest.mark.parametrize(
    ("version", "product_version"),
    [
        ("2026.2.4", "26.2.4"),
        ("2026.2.4a1", "26.2.4.101"),
        ("2026.2.4b2", "26.2.4.302"),
        ("2026.2.4rc1", "26.2.4.501"),
        ("2026.2.5a2.dev3", "26.2.5.0"),
        ("2026.2.5.dev3", "26.2.5.0"),
        ("2026.3", "26.3.0"),
        ("2027.1.0", "27.1.0"),
    ],
)
def test_product_version_fits_windows_installer(version: str, product_version: str) -> None:
    assert msi_identity(version).product_version == product_version


@pytest.mark.parametrize(
    "version",
    ["2026.2.4.post1", "2026.2.4+local", "v2026.2.4", "1.2.3", "2256.1.0", "2026.256.0"],
)
def test_refuses_what_it_cannot_carry(version: str) -> None:
    with pytest.raises(ValueError):
        msi_identity(version)


def test_finals_order_above_what_came_before() -> None:
    # Windows Installer compares the first three fields only.
    def key(version: str) -> tuple[int, ...]:
        return tuple(int(part) for part in msi_identity(version).product_version.split(".")[:3])

    assert key("2026.2.3") < key("2026.2.4rc1") <= key("2026.2.4") < key("2026.3.0a1")
    assert key("2026.9.0") < key("2027.1.0")


def test_product_code_is_per_version_and_stable() -> None:
    final = msi_identity("2026.2.4").product_code
    assert final == msi_identity("2026.2.4").product_code
    assert final != msi_identity("2026.2.4rc1").product_code
    assert final != msi_identity("2026.2.5").product_code
    assert msi_identity("2026.2.4").upgrade_code == UPGRADE_CODE


def test_guid_is_spelled_as_msi_spells_it() -> None:
    value = uuid.UUID("850c92d1-a856-4c71-a601-3832a2c8da9b")
    assert guid(value) == "{850C92D1-A856-4C71-A601-3832A2C8DA9B}"


def test_manifests_describe_the_release_asset() -> None:
    files = manifests("2026.2.4", "ab" * 32, datetime.date(2026, 11, 20))
    assert sorted(files) == [
        "CohoCMS.CLI.installer.yaml",
        "CohoCMS.CLI.locale.en-US.yaml",
        "CohoCMS.CLI.yaml",
    ]
    installer = files["CohoCMS.CLI.installer.yaml"]
    assert (
        "InstallerUrl: https://github.com/coho-cms/coho-cli/releases/download/"
        "release-v2026.2.4/coho-2026.2.4-windows-x64.msi" in installer
    )
    assert f"InstallerSha256: {'AB' * 32}" in installer
    assert f"ProductCode: '{guid(msi_identity('2026.2.4').product_code)}'" in installer
    assert "  DisplayVersion: 26.2.4\n" in installer
    assert "ReleaseDate: 2026-11-20\n" in installer
    for name, text in files.items():
        assert text.isascii(), name
        assert "PackageVersion: 2026.2.4\n" in text, name
        assert "ManifestVersion: 1.12.0\n" in text, name
        assert "\t" not in text, name


def test_manifest_folder_matches_winget_pkgs() -> None:
    assert manifest_folder(Path("out"), "2026.2.4") == Path("out/manifests/c/CohoCMS/CLI/2026.2.4")
