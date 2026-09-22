"""coho_cli — the ``coho`` command. A thin layer over ``coho_management_sdk``."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("coho-cli")
except PackageNotFoundError:  # pragma: no cover - editable/dev installs
    __version__ = "0.0.0"
