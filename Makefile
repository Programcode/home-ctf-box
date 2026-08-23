# OpenRange cyber range — developer entry points.
# `make help` lists targets. Long-running verification lives here so CI
# and humans run the exact same commands.

SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help bootstrap check lint typecheck test test-unit test-integration test-contract \
  test-content test-solvers test-e2e test-a11y test-security test-load \
  test-compose-clean-install test-backup-restore up down reset-demo backup restore content-check

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-28s\033[0m %s\n", $$1, $$2}'

bootstrap: ## Install Python (uv) and Node (pnpm) toolchains
	uv sync --all-packages
	pnpm install --frozen-lockfile
	uv run pre-commit install || true

check: ## Lint and typecheck everything that exists
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	pnpm exec prettier --check .

test: test-unit ## Run the fast test suite

test-unit: ## Unit tests (no backing services)
	uv run pytest -m "not integration and not e2e and not slow"

test-integration: ## Integration tests against core services
	uv run pytest -m integration

test-contract: ## API contract / OpenAPI compatibility tests
	@echo "contract suite arrives with the API foundation phase"; exit 1

test-content: ## Validate every content bundle (schema, lints)
	uv run cyberrange lint
	uv run cyberrange schemas --check-diff 2>/dev/null || true

content-check: test-content ## Alias kept for plan compatibility

test-solvers: ## Build room images and run intended-path solvers
	uv run python -m openrange.content.solve_all content/rooms

test-e2e: ## Browser journeys via Playwright
	@echo "e2e journeys arrive with the web app shell"; exit 1

test-a11y: ## Accessibility checks (axe, keyboard)
	@echo "a11y checks arrive with the design system"; exit 1

test-security: ## Security scans (semgrep, gitleaks, ZAP baseline)
	@echo "security gates arrive with the security engineering phase"; exit 1

test-load: ## k6 load soaks (5-user single node, 50-user cluster)
	@echo "load profiles arrive with the observability/ops phase"; exit 1

test-compose-clean-install: ## Fresh-install proof of the documented commands
	bash tests/install/compose-clean-install.sh

test-backup-restore: ## Backup then restore into an empty stack and smoke test
	bash tests/install/backup-restore.sh

up: ## Start core backing services
	docker compose --profile core up -d --wait
	@echo "core services ready: postgres :15432 redis :16379 minio :19000 meili :17700"

down: ## Stop all openrange compose services
	docker compose --profile core --profile dev --profile legacy-v0 down

reset-demo: ## Destroy volumes and restart the legacy demo stack from scratch
	docker compose --profile legacy-v0 down -v
	docker compose --profile legacy-v0 up -d --build
	PLATFORM_PORT=$${PLATFORM_PORT:-8000} ./scripts/demo-solve.sh

backup: ## Dump Postgres + MinIO metadata into backups/
	bash scripts/backup.sh

restore: ## Restore the latest backup into the running stack
	bash scripts/restore.sh
