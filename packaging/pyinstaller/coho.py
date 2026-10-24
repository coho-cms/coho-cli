"""What PyInstaller freezes: the same `main` the `coho` console script runs."""

from coho_cli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
