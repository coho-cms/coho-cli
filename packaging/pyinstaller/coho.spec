# PyInstaller spec for the standalone `coho` the GitHub release attaches: a folder with
# the executable, its own Python and every dependency, so nothing needs installing first.
#
# Build it from an environment with the coho-cli wheel installed, not from this checkout,
# so the binary carries exactly what PyPI users get:
#
#   uv venv .bin-venv && uv pip install --python .bin-venv dist/coho_cli-*.whl pyinstaller
#   .bin-venv/bin/python -m PyInstaller --noconfirm packaging/pyinstaller/coho.spec
#
# The result is dist/coho/, run as dist/coho/coho (coho.exe on Windows). A folder rather
# than --onefile: one file unpacks itself to a temporary directory on every run.

import os
import sys

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

hiddenimports = (
    # keyring finds its backends by entry point at run time, which analysis cannot see.
    collect_submodules("keyring.backends")
    # typer asks shellingham which shell it is in; shellingham imports a module per OS.
    + collect_submodules("shellingham")
)
if sys.platform == "win32":
    # The Windows Credential Manager backend reaches it lazily.
    hiddenimports += collect_submodules("win32ctypes")

# `coho --version` and keyring's entry points read the installed distributions' metadata.
datas = []
for distribution in ("coho-cli", "coho-management-sdk", "keyring"):
    datas += copy_metadata(distribution)

a = Analysis(
    [os.path.join(SPECPATH, "coho.py")],  # noqa: F821  SPECPATH is PyInstaller's
    hiddenimports=hiddenimports,
    datas=datas,
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="coho", console=True)  # noqa: F821
coll = COLLECT(exe, a.binaries, a.datas, name="coho")  # noqa: F821
