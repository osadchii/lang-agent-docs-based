# Repository Guidelines

## Project Structure & Source of Truth
- Docs in `docs/` are law. Read relevant docs before coding; code must match specs. If behavior changes, update code and docs in the same PR.
- Backend FastAPI in `backend/app/`: `api/` (endpoints), `core/` (config, logging); plan for `models/`, `repositories/`, `services/` per layered architecture.
- Tests in `backend/tests/`. Dev services via `docker-compose.dev.yml`. Example env: `.env.example`.

## Build, Test, and Development
- Setup: `cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- Run dev server: `uvicorn app.main:app --reload`
- Start Postgres/Redis: `docker-compose -f docker-compose.dev.yml up -d`
- Quality gates: `black app/ && isort app/ && ruff check app/ && mypy app/`
- Tests + coverage (required): `pytest --cov=app --cov-report=term-missing --cov-fail-under=85`
- Build image: `cd backend && docker build -t langagent-backend:latest .`

## Coding Style & Limits
- Python: 4 spaces, 100 col width, strict typing. Naming: `snake_case` (func/vars), `PascalCase` (classes), `UPPER_CASE` (constants).
- File limits: backend files ≤300 lines and one class per file; single responsibility. Split modules if exceeded. Frontend (when added): ≤250 lines per component.
- Use layered architecture: handlers only validate and delegate to services; business logic lives in `services/`.

## Testing & Coverage
- Pytest configured in `backend/pyproject.toml`; tests in `backend/tests/test_*.py` (classes `Test*`, funcs `test_*`). Markers: `unit`, `integration`.
- Minimum coverage: backend ≥85% (critical modules—auth, payments, repositories—100%). Frontend (when added) ≥75%, critical flows 100%.
- CI must pass before merge.

## Security & Configuration
- Never commit secrets. Use `.env` (copy from `.env.example`) and `app.core.config.Settings`.
- Do not trust Telegram `user_id`. Validate WebApp `initData` via HMAC per `docs/backend-auth.md`. Keep CORS strict (see `backend/app/main.py`).

## Commits & Pull Requests
- Use Conventional Commits. Examples: `feat(api): add health check`, `docs(api): update cards examples`.
- PRs require: clear description, linked issues, updated docs, green CI, coverage thresholds met, no hardcoded secrets, file-size limits respected, and at least 2 approvals.
