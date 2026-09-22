.PHONY: sync test lint type check format contracts

sync:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check packages
	uv run ruff format --check packages

format:
	uv run ruff format packages
	uv run ruff check --fix packages

type:
	uv run mypy

check: lint type test

# Re-vendor the contracts from a coho-data checkout and record its commit.
COHO_DATA ?= ../coho-data
contracts:
	cp $(COHO_DATA)/bff/src/main/resources/openapi/bff.yaml contracts/
	cp $(COHO_DATA)/api-authoring/src/main/resources/openapi/authoring.yaml contracts/
	cp $(COHO_DATA)/api-delivery-contract/src/main/resources/openapi/delivery.yaml contracts/
	git -C $(COHO_DATA) rev-parse HEAD > contracts/PIN
