# OpenRange cyber range — developer entry points.
# `make help` lists targets. Long-running verification lives here so CI
# and humans run the exact same commands.

SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help bootstrap check lint typecheck test test-unit test-integration test-contract \
  test-content test-solvers test-e2e test-a11y test-security test-load \
  test-compose-clean-install test-backup-restore up down reset-demo backup restore content-check \
  build-images push-images release-check

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
	@echo "contract suite is not wired yet; see docs/roadmap/implementation-status.md"; exit 1

test-content: ## Validate every content bundle (schema, lints)
	uv run cyberrange lint
	uv run cyberrange schemas --check-diff 2>/dev/null || true

content-check: test-content ## Alias kept for plan compatibility

test-solvers: ## Build room images and run intended-path solvers
	uv run python -m openrange.content.solve_all content/rooms

test-e2e: ## Browser journeys via Playwright (starts the web app)
	pnpm --filter web test:e2e

test-a11y: ## Accessibility checks (axe and keyboard) via Playwright
	pnpm --filter web exec playwright test tests/e2e/a11y.spec.ts tests/e2e/keyboard-journey.spec.ts --project=chromium

test-security: ## Security scans (bandit, pip-audit, pnpm audit, gitleaks)
	@echo "run the checks in .github/workflows/security.yml; this target is not a local runner yet"; exit 1

test-load: ## k6 load soaks (5-user single node, 50-user cluster)
	@echo "load profiles are not implemented yet; see docs/roadmap/implementation-status.md"; exit 1

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

IMAGE_REGISTRY ?= ghcr.io
# ghcr.io requires lowercase repository paths; derive from origin when possible.
IMAGE_OWNER ?= $(shell git config --get remote.origin.url | sed -E 's#.*[:/]([^/]+)/[^/]+(\.git)?$$#\1#' | tr '[:upper:]' '[:lower:]')
IMAGE_TAG ?= dev

build-images: ## Build the three production images locally (docker build)
	docker build -f docker/Dockerfile.api -t $(IMAGE_REGISTRY)/$(IMAGE_OWNER)/openrange-api:$(IMAGE_TAG) .
	docker build -f docker/Dockerfile.web -t $(IMAGE_REGISTRY)/$(IMAGE_OWNER)/openrange-web:$(IMAGE_TAG) .
	docker build -f docker/Dockerfile.gateway -t $(IMAGE_REGISTRY)/$(IMAGE_OWNER)/openrange-gateway:$(IMAGE_TAG) .

push-images: ## Push the three production images (requires IMAGE_TAG and GHCR auth)
	test "$(IMAGE_TAG)" != dev || { echo "refusing to push :dev; set IMAGE_TAG=vX.Y.Z"; exit 1; }
	for c in api web gateway; do \
		docker push $(IMAGE_REGISTRY)/$(IMAGE_OWNER)/openrange-$$c:$(IMAGE_TAG); \
	done

release-check: ## Packaging gates: ruff, prettier, shell syntax, compose validation
	uv run ruff check .
	pnpm exec prettier --check .
	@for f in scripts/*.sh scripts/operations/*.sh tests/install/*.sh; do \
		bash -n "$$f" || exit 1; \
	done
	@if [ -f .env ]; then created=0; else \
		printf 'POSTGRES_PASSWORD=release-check\nOPENRANGE_S3_ACCESS_KEY=release-check\nOPENRANGE_S3_SECRET_KEY=release-check\nOPENRANGE_MEILI_MASTER_KEY=release-check\n' > .env; \
		created=1; \
	fi; \
	docker compose -f infra/compose/production.yml --env-file .env --profile ops config > /dev/null; \
	rc=$$?; \
	if [ "$$created" = "1" ]; then rm -f .env; fi; \
	[ $$rc -eq 0 ] && echo "infra/compose/production.yml validates"; \
	exit $$rc