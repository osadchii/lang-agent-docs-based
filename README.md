# ✨ Lang Agent Backend Starter ✨
> Телеграм-бот и Mini App для изучения языков — инфраструктура готова, осталось вселить в неё интеллект.

## 🏗️ Что уже готово
- Структура `backend/app/{api,core,models,repositories,services}` и тестовый пакет
- Базовая конфигурация `Settings` (строгая типизация, валидация CORS, единый источник правды)
- Инженерные соглашения: `pyproject.toml`, `requirements.txt`, `.editorconfig`, `.gitignore`, `.env.example`
- GitHub Actions workflow `.github/workflows/backend-deploy.yml` (тесты на каждом push/PR, build & GHCR push + автодеплой на сервер для `main`)
- Согласование с документацией в `docs/` — текущий репозиторий стартует строго по плану `to-do.md`
- Продовый `backend/Dockerfile` + корневой `docker-compose.yml` (backend/db/redis + Loki/Promtail/Grafana + Traefik, healthchecks, Alembic перед стартом)
- Провиженинг Grafana (`infra/`) с готовым дашбордом (RPS, p95 latency, 4xx/5xx, top endpoints)
- Traefik reverse proxy с автоматическим Let's Encrypt сертификатом для Grafana (наружу торчит только HTTPS)

## 📁 Структура репозитория
```text
.
├── README.md
├── docker-compose.yml       # Продовый стак backend/db/redis + Loki/Promtail/Grafana + Traefik
├── docker-compose.local.yml # Локальные Postgres + Redis для разработки
├── infra/                   # Конфиги наблюдаемости (Loki, Promtail, Grafana)
├── docs/                     # Источник правды по архитектуре, API и процессам
├── .github/
│   └── workflows/            # CI pipeline (backend-deploy.yml)
└── backend/
    ├── Dockerfile           # Продовый образ backend (uvicorn + alembic upgrade head)
    ├── docker-entrypoint.sh # Точка входа: прогон миграций и запуск сервера
    ├── app/
    │   ├── api/             # FastAPI роуты (задача #2+)
    │   ├── core/            # Config, логирование, middleware
    │   ├── models/          # SQLAlchemy модели (задача #4)
    │   ├── repositories/    # DAL + Unit of Work
    │   └── services/        # Бизнес-логика и интеграции
    └── tests/               # Pytest/pytest-asyncio
```

## ⚙️ Технологический стек
- Python 3.11+, FastAPI, SQLAlchemy 2.x (async), Alembic, Redis, OpenAI SDK
- Чистый code style: Black, isort, Ruff, mypy (strict) из `pyproject.toml`
- Secrets и конфиги через `pydantic-settings` + `.env` (см. `.env.example`)

## 🚀 Быстрый старт (локально)
1. ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
2. Создайте `backend/.env` или корневой `.env` на основе `.env.example`
3. Проверьте конфиг: `python - <<'PY'
from app.core.config import settings
print(settings.project_name, settings.environment, settings.cors_origins)
PY`
4. Запускаем проверки (подготовлены, код появится в следующих задачах):
   - `ruff check app`
   - `black --check app`
   - `mypy app`
5. (Опционально, но рекомендуется) включите автоматические проверки перед коммитами:
   ```bash
   cd backend
   source .venv/bin/activate  # либо .\.venv\Scripts\Activate.ps1 в PowerShell
   pre-commit install
   ```
### 🐳 Продовый docker-compose (backend + db + redis + observability)
1. Скопируйте `.env.example` → `.env`, заполните `POSTGRES_*`, `BACKEND_IMAGE`, `BACKEND_IMAGE_TAG`, `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`, `GRAFANA_DOMAIN` и `TRAEFIK_ACME_EMAIL`. Для работы внутри Docker-сети обновите `DATABASE_URL` и `REDIS_URL` на `postgresql+asyncpg://<user>:<pass>@db:5432/<db>` и `redis://redis:6379/0`.
2. Скопируйте на сервер сам `docker-compose.yml` вместе с каталогом `infra/` — Grafana и Loki читают конфиги именно оттуда.
3. Откройте на сервере порты `80`/`443` (Traefik делает HTTP-01 проверку и раздаёт HTTPS для Grafana).
4. Получите и поднимите стек с образами из GHCR:
   ```bash
   docker compose pull backend
   docker compose up -d backend db redis loki promtail grafana
   docker compose up -d traefik
   ```
   > Если нужна локальная проверка до пуша в GHCR, пересоберите образ командами `docker compose build backend` и `docker compose up ...`.
5. Проверьте здоровье и логи:
   ```bash
   docker compose ps
   docker compose logs -f backend
   docker compose logs -f promtail
   docker compose logs -f traefik
   ```
   Точка входа `docker-entrypoint.sh` автоматически выполняет `alembic upgrade head` перед запуском `uvicorn`.

#### 📊 Observability stack (Grafana + Loki)
- Grafana доступна только по `https://<GRAFANA_DOMAIN>` через Traefik; логин/пароль берутся из `GRAFANA_ADMIN_USER/PASSWORD`.
- Loki хранит данные в volume `loki_data` и принимает пуши Promtail только по внутренней сети compose (`app-network`). Публичные порты для Loki не открываются.
- Promtail подключается к Docker socket и забирает JSON-логи контейнера `backend`, парсит поля (`http_method`, `status_code`, `duration_ms`, `request_id`) и пушит их в Loki.
- При первом старте Grafana автоматически импортирует datasoure `Loki` и дашборд `Backend Observability` из `infra/grafana/provisioning/dashboards/backend-observability.json` (RPS, p95 latency, 4xx/5xx, top endpoints).
- Traefik автоматически выпускает Let's Encrypt сертификат для `GRAFANA_DOMAIN`, пробрасывает только Grafana наружу (`https://<GRAFANA_DOMAIN>`), закрывая backend/infra из внешней сети. Для повторных запусков сертификаты кэшируются в volume `traefik_acme`.
- Переменная `DOCKER_API_VERSION=1.44` проброшена в Traefik, чтобы он общался с современным Docker API; при более старом демоне можно понизить значение, но рекомендуется обновить Docker.

### 🔐 GitHub Secrets для CI/CD
Добавьте в Settings → Secrets and variables → Actions:
- `GHCR_USERNAME` — имя владельца GHCR (для репо `osadchii/lang-agent-docs-based` укажите `osadchii`).
- `GHCR_TOKEN` — GitHub Personal Access Token с правами `write:packages` (рекомендуется отдельный fine-grained token).
- `SSH_PRIVATE_KEY_LANG_AGENT` — приватный ключ с доступом к серверу деплоя (read/write в `/opt/lang-agent`).
- `SSH_HOST` — адрес сервера.
- `SSH_PORT` — SSH порт (обычно `22`).
- `SSH_USER` — пользователь, от имени которого выполняются `scp` / `ssh` команды.

## 📚 Документация (обязательна к прочтению перед задачами)
| Блок | Цель | Файл |
| ---- | ---- | ---- |
| Vision & цели | Что мы строим и почему | `docs/product-vision.md`
| Архитектура | Взаимодействие сервисов | `docs/architecture.md`
| API | Контракты REST | `docs/backend-api.md`
| Данные | Модели и миграции | `docs/backend-database.md`
| Процессы | Code style, CI/CD, деплой | `docs/development-guidelines.md`, `docs/ci-cd.md`, `docs/deployment.md`

## ✅ Definition of Done (для каждой задачи из `to-do.md`)
- Код форматируется `black`, `isort`, `ruff`, типы проверяет `mypy`
- Тесты `pytest --cov=app --cov-fail-under=85` зелёные
- Обновлены релевантные документы в `docs/`
- CI/CD pipeline зелёный, секреты только в `.env`

## 🗺️ Roadmap (из `to-do.md`)
1. ✅ **Скелет репозитория**
2. ✅ FastAPI + `/health`, CORS и middleware
3. ✅ Логирование и request tracing
4. ✅ PostgreSQL + Alembic + репозитории `users` / `conversation_history`
5. ✅ Docker Compose для локального окружения + Makefile
6. ✅ Pytest + quality gates
7. ✅ CI: backend tests (GitHub Actions)
8. ✅ Образы и продовый docker-compose
9. ✅ CI: backend deploy (build -> GHCR)
10. ⏳ ... (бот, интеграции, продовый релиз)

> 💡 Следуя этому README и документации внутри `docs/`, можно безопасно продолжать реализацию следующих этапов без расхождений.
