"""The winget manifests for a released Coho CLI MSI, laid out as microsoft/winget-pkgs wants.

    python packaging/windows/winget_manifest.py 2026.2.4 dist/coho-2026.2.4-windows-x64.msi out

writes out/manifests/c/CohoCMS/CLI/2026.2.4/ with the version, installer, and default
locale manifests. Copy that folder into a fork of winget-pkgs at the same path and open
a pull request; CONTRIBUTING.md has the steps. The installer URL is the GitHub release
asset, so generate the manifests only for a tag whose release carries this exact MSI:
the hash must match what winget downloads.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
from pathlib import Path

from msi_version import guid, msi_identity

PACKAGE_IDENTIFIER = "CohoCMS.CLI"
MANIFEST_VERSION = "1.12.0"
REPOSITORY = "https://github.com/coho-cms/coho-cli"


def _header(manifest_type: str) -> str:
    schema = f"https://aka.ms/winget-manifest.{manifest_type}.{MANIFEST_VERSION}.schema.json"
    return f"# yaml-language-server: $schema={schema}\n\n"


def manifests(version: str, msi_sha256: str, release_date: datetime.date) -> dict[str, str]:
    """The three manifests by file name. Every value is plain ASCII, so no YAML quoting rules
    beyond the GUIDs' braces come into it."""
    identity = msi_identity(version)
    product_code = guid(identity.product_code)
    tag = f"release-v{version}"
    msi_name = f"coho-{version}-windows-x64.msi"

    version_manifest = _header("version") + (
        f"PackageIdentifier: {PACKAGE_IDENTIFIER}\n"
        f"PackageVersion: {version}\n"
        "DefaultLocale: en-US\n"
        "ManifestType: version\n"
        f"ManifestVersion: {MANIFEST_VERSION}\n"
    )

    # DisplayVersion: Apps & features shows the MSI's ProductVersion (26.2.4), not
    # 2026.2.4, and winget needs telling the two are one version.
    installer_manifest = _header("installer") + (
        f"PackageIdentifier: {PACKAGE_IDENTIFIER}\n"
        f"PackageVersion: {version}\n"
        "InstallerType: wix\n"
        "Scope: machine\n"
        "InstallModes:\n"
        "- interactive\n"
        "- silent\n"
        "- silentWithProgress\n"
        "UpgradeBehavior: install\n"
        "ElevationRequirement: elevatesSelf\n"
        "Commands:\n"
        "- coho\n"
        f"ProductCode: '{product_code}'\n"
        f"ReleaseDate: {release_date.isoformat()}\n"
        "AppsAndFeaturesEntries:\n"
        "- DisplayName: Coho CLI\n"
        "  Publisher: Coho\n"
        f"  DisplayVersion: {identity.product_version}\n"
        f"  ProductCode: '{product_code}'\n"
        f"  UpgradeCode: '{guid(identity.upgrade_code)}'\n"
        "Installers:\n"
        "- Architecture: x64\n"
        f"  InstallerUrl: {REPOSITORY}/releases/download/{tag}/{msi_name}\n"
        f"  InstallerSha256: {msi_sha256.upper()}\n"
        "ManifestType: installer\n"
        f"ManifestVersion: {MANIFEST_VERSION}\n"
    )

    locale_manifest = _header("defaultLocale") + (
        f"PackageIdentifier: {PACKAGE_IDENTIFIER}\n"
        f"PackageVersion: {version}\n"
        "PackageLocale: en-US\n"
        "Publisher: Coho\n"
        "PublisherUrl: https://github.com/coho-cms\n"
        f"PublisherSupportUrl: {REPOSITORY}/issues\n"
        "PackageName: Coho CLI\n"
        f"PackageUrl: {REPOSITORY}\n"
        "License: Apache-2.0\n"
        f"LicenseUrl: {REPOSITORY}/blob/HEAD/LICENSE\n"
        "ShortDescription: The coho command for managing Coho accounts, projects, branches, "
        "releases, and content from a terminal.\n"
        "Moniker: coho\n"
        "Tags:\n"
        "- cli\n"
        "- cms\n"
        "- content\n"
        "- headless-cms\n"
        f"ReleaseNotesUrl: {REPOSITORY}/releases/tag/{tag}\n"
        "Documentations:\n"
        "- DocumentLabel: Documentation\n"
        f"  DocumentUrl: {REPOSITORY}/tree/HEAD/docs\n"
        "ManifestType: defaultLocale\n"
        f"ManifestVersion: {MANIFEST_VERSION}\n"
    )

    return {
        f"{PACKAGE_IDENTIFIER}.yaml": version_manifest,
        f"{PACKAGE_IDENTIFIER}.installer.yaml": installer_manifest,
        f"{PACKAGE_IDENTIFIER}.locale.en-US.yaml": locale_manifest,
    }


def manifest_folder(out: Path, version: str) -> Path:
    """Where winget-pkgs keeps them: manifests/<first letter>/<Publisher>/<Name>/<version>."""
    publisher, name = PACKAGE_IDENTIFIER.split(".", 1)
    return out / "manifests" / publisher[0].lower() / publisher / name / version


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("version", help="the coho-cli version, such as 2026.2.4")
    parser.add_argument("msi", type=Path, help="the MSI the release carries")
    parser.add_argument("out", type=Path, help="the folder to write manifests/ into")
    parser.add_argument(
        "--release-date",
        type=datetime.date.fromisoformat,
        default=datetime.datetime.now(datetime.UTC).date(),
        help="YYYY-MM-DD; today (UTC) by default",
    )
    args = parser.parse_args()

    expected = f"coho-{args.version}-windows-x64.msi"
    if args.msi.name != expected:
        parser.error(f"{args.msi.name} is not {expected}: the URL would not name this file")
    sha256 = hashlib.sha256(args.msi.read_bytes()).hexdigest()

    folder = manifest_folder(args.out, args.version)
    folder.mkdir(parents=True, exist_ok=True)
    for file_name, text in manifests(args.version, sha256, args.release_date).items():
        (folder / file_name).write_text(text, encoding="utf-8", newline="\n")
        print(folder / file_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
