.PHONY: sync test lint type check format build clean

sync:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

type:
	uv run mypy

check: lint type test

# The wheel and the sdist, into dist/.
build:
	uv build --out-dir dist
	uvx twine check --strict dist/*.whl dist/*.tar.gz

clean:
	rm -rf dist build .pytest_cache .ruff_cache .mypy_cache

# The contracts live with the library, in coho-management-sdk-python.
