"""The Windows Installer identity of a coho-cli version: ProductVersion, ProductCode, UpgradeCode.

Windows Installer reads ProductVersion as major.minor.build, with major and minor at most
255 and build at most 65535, and compares only those three fields. A fourth field is shown
in Apps & features but ignored when deciding what upgrades what. 2026.2.4 cannot be a
ProductVersion, so the year loses its century: 2026.2.4 installs as 26.2.4.

A pre-release adds a fourth field naming its stage, so it reads apart from the final in
Apps & features: a1 is 26.2.4.101, b2 is 26.2.4.302, rc1 is 26.2.4.501. A development
build of any of them (2026.2.5a2.dev3) has a fourth field of 0. As Windows Installer
ignores the fourth field, all of these are the same version to it; the MSI allows
same-version upgrades, so the final installs over its release candidate.

ProductCode must differ for every version, because every install is a major upgrade. It
is derived from the version, so the same version always has the same code and the winget
manifest can name it without opening the MSI. UpgradeCode never changes: it is what ties
every Coho CLI MSI together as one product.

Run as a script, it prints `name=value` lines for $GITHUB_OUTPUT:

    python packaging/windows/msi_version.py 2026.2.4rc1
"""

from __future__ import annotations

import re
import sys
import uuid
from dataclasses import dataclass

# ⛔ Never change this. Every Coho CLI MSI ever shipped carries it, and an MSI with a
# different one installs beside the old CLI instead of replacing it.
UPGRADE_CODE = uuid.UUID("850C92D1-A856-4C71-A601-3832A2C8DA9B")

# The fourth ProductVersion field per pre-release stage, plus its number.
_STAGES = {"a": 100, "b": 300, "rc": 500}

# The versions hatch-vcs builds from our tags and commits, in PEP 440's normal form:
# 2026.2.4, 2026.2.4a1, 2026.2.4b2, 2026.2.4rc1, and any of them with .devN after.
_VERSION = re.compile(
    r"^(?P<year>\d{4})\.(?P<release>\d+)(?:\.(?P<patch>\d+))?"
    r"(?:(?P<stage>a|b|rc)(?P<number>\d+))?"
    r"(?:\.dev(?P<dev>\d+))?$"
)


@dataclass(frozen=True)
class MsiIdentity:
    version: str
    product_version: str
    product_code: uuid.UUID

    @property
    def upgrade_code(self) -> uuid.UUID:
        return UPGRADE_CODE


def msi_identity(version: str) -> MsiIdentity:
    match = _VERSION.match(version)
    if match is None:
        raise ValueError(
            f"{version!r} is not a coho-cli version this MSI can carry: expected forms like "
            "2026.2.4, 2026.2.4a1, 2026.2.4rc1 or 2026.2.5a1.dev3"
        )
    major = int(match["year"]) - 2000
    minor = int(match["release"])
    build = int(match["patch"] or 0)
    if not (0 <= major <= 255 and minor <= 255 and build <= 65535):
        raise ValueError(f"{version!r} does not fit Windows Installer's version limits")

    fields = [major, minor, build]
    if match["dev"] is not None:
        fields.append(0)
    elif match["stage"] is not None:
        number = int(match["number"])
        if number > 99:
            raise ValueError(f"{version!r}: a pre-release number above 99 does not fit")
        fields.append(_STAGES[match["stage"]] + number)

    return MsiIdentity(
        version=version,
        product_version=".".join(str(field) for field in fields),
        product_code=uuid.uuid5(UPGRADE_CODE, version),
    )


def guid(value: uuid.UUID) -> str:
    """A GUID the way MSI tables and winget manifests spell it: braced, upper case."""
    return "{" + str(value).upper() + "}"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: msi_version.py VERSION", file=sys.stderr)
        return 2
    try:
        identity = msi_identity(argv[1])
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"product_version={identity.product_version}")
    print(f"product_code={guid(identity.product_code)}")
    print(f"upgrade_code={guid(identity.upgrade_code)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
