.PHONY: local-up local-down lint test

local-up:
	docker compose -f docker-compose.local.yml up -d

local-down:
	docker compose -f docker-compose.local.yml down --remove-orphans

lint:
	cd backend && ruff check app && black --check app && isort --check-only app && mypy app

test:
	cd backend && pytest --cov=app --cov-fail-under=84
