# ✨ Lang Agent Backend Starter ✨
> Телеграм-бот и Mini App для изучения языков — инфраструктура готова, осталось вселить в неё интеллект.

## 🏗️ Что уже готово
- Структура `backend/app/{api,core,models,repositories,services}` и тестовый пакет
- Базовая конфигурация `Settings` (строгая типизация, жёсткий CORS — Telegram WebApp + PROD origin + localhost whitelist для `APP_ENV=local/test`, лимит тела запроса, security headers/HSTS)
- Полный перечень переменных окружения с комментариями (`.env.example` + README + `docs/deployment.md`) и жёсткой валидацией при старте
- Инженерные соглашения: `pyproject.toml`, `requirements.txt`, `.editorconfig`, `.gitignore`, `.env.example`
- GitHub Actions workflow `.github/workflows/backend-deploy.yml` (тесты на каждом push/PR, build & GHCR push + автодеплой на сервер для `main` + Telegram-уведомления по итогам тестов/сборки/деплоя)
- Согласование с документацией в `docs/` — текущий репозиторий стартует строго по плану `to-do.md`
- Продовый `backend/Dockerfile` + корневой `docker-compose.yml` (backend/db/redis + Loki 3 + Promtail 3 + Grafana 12 + Nginx proxy, healthchecks, Alembic перед стартом)
- Prometheus-инструментация /metrics через prometheus_fastapi_instrumentator (с request_id в гистограммах)
- Telegram Bot API интеграция: `python-telegram-bot` 20.8, вебхук `POST /telegram-webhook/{bot_token}` + helper для polling (`python -m app.telegram.polling`), конфигурация по `docs/backend-telegram.md`
- Глобальные обработчики ошибок FastAPI → единый JSON-контракт (`docs/backend-api.md`) + защита от слишком больших тел запросов
- Провиженинг Grafana 12 (`infra/`) с готовым дашбордом (RPS, p95 latency, 4xx/5xx, top endpoints)
- Nginx reverse proxy + ACME companion, который автоматически выпускает Let's Encrypt сертификат для Grafana (наружу торчит только HTTPS)

## 📁 Структура репозитория
```text
.
├── README.md
├── docker-compose.yml       # Продовый стак backend/db/redis + Loki/Promtail/Grafana + Nginx proxy
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
2. Скопируйте `.env.example` → `.env` (в `backend/` или в корне), заполните обязательные переменные: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`. Для остальных можно оставить значения по умолчанию (см. таблицу ниже).
3. Проверьте конфиг — приложение упадёт на старте, если чего‑то не хватает:
   ```bash
   python - <<'PY'
from app.core.config import settings
print(settings.project_name, settings.environment, settings.cors_origins)
PY
   ```
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
6. Проверьте, что /metrics уже отдаёт данные:
   `ash
   curl http://localhost:8000/metrics | head
   `
   Вы должны увидеть http_requests_total и pp_request_latency_seconds c
equest_id (exemplar) — этого достаточно для подключения Prometheus.
7. Telegram Bot:
   - Для продакшена укажите `TELEGRAM_WEBHOOK_URL` — при старте backend автоматически вызовет `setWebhook` по инструкции из `docs/backend-telegram.md`.
   - Для локальной отладки запускайте long polling в отдельном терминале: `cd backend && python -m app.telegram.polling` (использует токен и настройки из `.env`).
   - Обработчик `/start` уже доступен («Привет!»), остальная логика реализуется на шагах 16+.
### 🐳 Продовый docker-compose (backend + db + redis + observability)
1. Скопируйте `.env.example` → `.env`, заполните `POSTGRES_*`, `BACKEND_IMAGE`, `BACKEND_IMAGE_TAG`, `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`, `GRAFANA_DOMAIN` и `TRAEFIK_ACME_EMAIL` (email для Let's Encrypt). Для работы внутри Docker-сети обновите `DATABASE_URL` и `REDIS_URL` на `postgresql+asyncpg://<user>:<pass>@db:5432/<db>` и `redis://redis:6379/0`.
2. Скопируйте на сервер сам `docker-compose.yml` вместе с каталогом `infra/` — Grafana и Loki читают конфиги именно оттуда.
3. Откройте на сервере порты `80`/`443` (nginx-proxy+acme-companion выполняют HTTP-01 проверку и раздают HTTPS для Grafana).
4. Получите и поднимите стек с образами из GHCR:
   ```bash
   docker compose pull backend
   docker compose up -d backend db redis loki promtail grafana
   docker compose up -d nginx nginx-acme
   ```
   > Если нужна локальная проверка до пуша в GHCR, пересоберите образ командами `docker compose build backend` и `docker compose up ...`.
5. Проверьте здоровье и логи:
   ```bash
   docker compose ps
   docker compose logs -f backend
   docker compose logs -f promtail
   docker compose logs -f nginx
   docker compose logs -f nginx-acme
   ```
   Точка входа `docker-entrypoint.sh` автоматически выполняет `alembic upgrade head` перед запуском `uvicorn`.

#### 📊 Observability stack (Grafana 12 + Loki 3)
- Grafana 12 доступна только по `https://<GRAFANA_DOMAIN>` благодаря связке `nginx-proxy` + `acme-companion`; логин/пароль берутся из `GRAFANA_ADMIN_USER/PASSWORD`.
- Loki хранит данные в volume `loki_data` и принимает пуши Promtail только по внутренней сети compose (`app-network`). Публичные порты для Loki не открываются.
- Promtail подключается к Docker socket и забирает JSON-логи контейнера `backend`, парсит поля (`http_method`, `status_code`, `duration_ms`, `request_id`) и пушит их в Loki.
- /metrics доступен локально: prometheus_fastapi_instrumentator снимает latency/кол-во запросов и сохраняет
equest_id (exemplar) для корреляции с логами.
- При первом старте Grafana 12 автоматически импортирует datasoure `Loki` и дашборд `Backend Observability` из `infra/grafana/provisioning/dashboards/backend-observability.json` (RPS, p95 latency, 4xx/5xx, top endpoints).
- Nginx proxy автоматически выпускает Let's Encrypt сертификат для `GRAFANA_DOMAIN`, пробрасывает только Grafana наружу (`https://<GRAFANA_DOMAIN>`), закрывая backend/infra из внешней сети. Для повторных запусков сертификаты кэшируются в volume `nginx_certs` / `nginx_acme`.

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

## 🔐 Переменные окружения
Полный список значений описан в `.env.example` и `docs/deployment.md`. Ниже краткая шпаргалка для backend‑службы:

| Переменная | Обязательна | Назначение | Значение по умолчанию |
| --- | --- | --- | --- |
| `PROJECT_NAME` | нет | Название сервиса в OpenAPI/логах | `Lang Agent Backend` |
| `APP_ENV` | нет | Окружение (`local/test/staging/production`) | `local` |
| `DEBUG` | нет | Включает swagger + подробные ошибки | `false` |
| `API_V1_PREFIX` | нет | Префикс REST API | `/api` |
| `LOG_LEVEL` | нет | Глобальный уровень логирования | `INFO` |
| `DATABASE_URL` | **да** | Подключение к PostgreSQL (`asyncpg`) | — |
| `REDIS_URL` | **да** | Подключение к Redis | — |
| `SECRET_KEY` | **да** | JWT‑секрет (openssl rand -hex 32) | — |
| `JWT_ALGORITHM` | нет | Алгоритм подписи токенов | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | нет | TTL access токена | `30` |
| `TELEGRAM_BOT_TOKEN` | **да** | Токен бота из BotFather | — |
| `TELEGRAM_WEBHOOK_URL` | нет | Абсолютный URL вебхука | — |
| `OPENAI_API_KEY` | **да** | Ключ OpenAI для LLM | — |
| `ANTHROPIC_API_KEY` | нет | Ключ Claude (опционально) | — |
| `LLM_MODEL` | нет | Модель по умолчанию | `gpt-4.1-mini` |
| `LLM_TEMPERATURE` | нет | Творчество LLM (`0..1`) | `0.7` |
| `PRODUCTION_APP_ORIGIN` | нет | Боевой origin Mini App | — |
| `BACKEND_CORS_ORIGINS` | нет | Локальный whitelist (`http://localhost:<port>`, учитывается только при `APP_ENV=local/test`) | `http://localhost:4173` |
| `MAX_REQUEST_BYTES` | нет | Лимит тела запроса (байты, default 1 MiB) | `1048576` |
| `STRIPE_SECRET_KEY` | нет | Платежи (будет нужно для подписок) | — |
| `STRIPE_WEBHOOK_SECRET` | нет | Проверка подписей Stripe | — |
| `STRIPE_PRICE_ID_BASIC/PREMIUM` | нет | Тарифы в Stripe | — |

Инфраструктурные переменные (docker-compose, CI/CD):

| Переменная | Назначение |
| --- | --- |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Учётки Postgres внутри `docker-compose.yml` |
| `BACKEND_IMAGE`, `BACKEND_IMAGE_TAG` | Какой образ backend тянуть на сервере |
| `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`, `GRAFANA_DOMAIN`, `TRAEFIK_ACME_EMAIL` | Настройки наблюдаемости и SSL |
| `TELEGRAM_DEPLOY_CHAT_ID`, `CI_BOT_TOKEN` | GitHub Secrets для Telegram-уведомлений CI/CD (tests/build/deploy статусы) |

> Если переменная обязательна и не заполнена, `app.core.config.Settings` выбросит читаемое исключение при старте. Это же поведение используется в тестах и CI, поэтому несогласованные конфиги ловим сразу.
