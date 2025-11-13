# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ КРИТИЧНО: Соответствие документации

**ПЕРЕД НАЧАЛОМ ЛЮБОЙ РАБОТЫ** обязательно изучить релевантную документацию из `../docs/`:

### Источник правды - документация

- **Документация имеет приоритет над кодом** - если код не соответствует документации, код должен быть исправлен (либо документация должна быть обновлена через согласованный процесс)
- **Все архитектурные решения** должны соответствовать `docs/architecture.md`
- **Все API endpoints** должны строго следовать спецификации из `docs/backend-api.md`
- **Схема БД и модели** должны соответствовать `docs/backend-database.md`
- **Бизнес-логика** должна реализовывать use cases из `docs/use-cases.md`
- **Принципы разработки** описаны в `docs/development-guidelines.md`

### Обязательные документы для backend разработки

При работе с backend **ВСЕГДА** проверяйте эти документы:

1. **`docs/architecture.md`** - общая архитектура системы, взаимодействие компонентов
2. **`docs/backend-api.md`** - REST API спецификация (endpoints, request/response formats)
3. **`docs/backend-database.md`** - схема базы данных, модели, связи
4. **`docs/backend-telegram.md`** - интеграция с Telegram Bot API и Mini App
5. **`docs/backend-llm.md`** - работа с LLM (промпты, форматы, обработка)
6. **`docs/backend-auth.md`** - аутентификация и авторизация
7. **`docs/development-guidelines.md`** - code style, тестирование, принципы разработки

### Специализированные документы (по необходимости)

- **`docs/backend-flashcards.md`** - система карточек и алгоритмы повторения
- **`docs/backend-exercises.md`** - типы упражнений и их логика
- **`docs/backend-bot-responses.md`** - формирование ответов бота
- **`docs/backend-subscriptions.md`** - монетизация и подписки
- **`docs/ci-cd.md`** - CI/CD pipeline и автоматизация
- **`docs/deployment.md`** - процесс деплоя и окружения

### Workflow при работе с задачами

1. **Прочитать** релевантные разделы документации
2. **Убедиться** что решение соответствует архитектуре
3. **Реализовать** согласно спецификациям
4. **Проверить** что код следует `development-guidelines.md`
5. **Покрыть тестами** согласно требованиям (минимум 80% coverage)
6. **Обновить README.md** если изменения затрагивают:
   - Структуру проекта (новые директории, модули)
   - API endpoints или публичный интерфейс
   - Команды разработки или deployment
   - Конфигурацию или зависимости
   - Процессы и workflow

### ⚠️ ВАЖНО: Поддержка README в актуальном состоянии

**После любых изменений в проекте:**
- Проверь, нужно ли обновить `README.md`
- README должен отражать текущее состояние проекта
- Особенно важно обновлять:
  - Список features и возможностей
  - Инструкции по установке и запуску
  - Структуру проекта (если изменилась)
  - Примеры использования API
  - Требования и зависимости

### ⚠️ Git Workflow

**ВАЖНО: НЕ СОЗДАВАЙ GIT КОММИТЫ**

- Claude не должен использовать команды `git add`, `git commit`, `git push`
- Пользователь сам создает коммиты и управляет git
- После завершения задачи просто сообщи пользователю, что изменения готовы для коммита
- Можно использовать `git status`, `git diff` для информации, но НЕ изменяющие команды

## Project Overview

This is a FastAPI-based backend for the Lang Agent Telegram bot and Mini App - an LLM-powered language learning application. The backend integrates with Telegram Bot API, OpenAI, PostgreSQL, and Redis.

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install with dev dependencies (recommended for development)
pip install -e ".[dev]"
```

### Database Migrations
```bash
# Run migrations (uses DATABASE_URL from .env)
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Rollback one migration
alembic downgrade -1
```

### Running the Application
```bash
# Development server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode (uses docker-entrypoint.sh which runs migrations first)
./docker-entrypoint.sh
```

### Testing
```bash
# Run all tests with coverage (CI requires 80% coverage minimum)
pytest tests/ -v --cov=app --cov-report=term --cov-fail-under=80

# Run specific test file
pytest tests/services/test_user_service.py -v

# Run specific test function
pytest tests/services/test_user_service.py::test_register_user -v

# Run tests without coverage for faster iteration
pytest tests/ -v
```

### Code Quality
```bash
# Run all linters (Ruff does formatting, linting, and import sorting)
ruff check app/ tests/
ruff format app/ tests/

# Type checking with mypy (strict mode enabled)
mypy app/

# Auto-fix issues where possible
ruff check --fix app/ tests/
```

## Architecture

### Layered Structure

The codebase follows a clean architecture with clear separation of concerns:

1. **Models** (`app/models/`) - SQLAlchemy ORM models representing database tables
   - Use `Base` from `app.models.base` as the declarative base
   - `TimestampMixin` adds created_at/updated_at timestamps
   - `SoftDeleteMixin` adds deleted/deleted_at columns for soft deletes
   - `GUID` type provides cross-database UUID support (native for PostgreSQL, CHAR(36) for SQLite)

2. **Repositories** (`app/repositories/`) - Data access layer
   - Extend `BaseRepository[ModelT]` from `app.repositories.base`
   - Handle all database queries and CRUD operations
   - Accept `AsyncSession` as dependency injection
   - Return model instances or None

3. **Services** (`app/services/`) - Business logic layer
   - Orchestrate repository calls and implement business rules
   - Accept repository instances via dependency injection
   - Should not directly touch SQLAlchemy sessions

4. **API Routes** (`app/api/routes/`) - HTTP endpoints
   - FastAPI routers defining REST API endpoints
   - Use `get_session()` dependency for database access
   - Instantiate services with repositories
   - All routers are aggregated in `app/api/routes/__init__.py`

5. **Core** (`app/core/`) - Shared infrastructure
   - `config.py` - Environment-driven configuration using Pydantic Settings
   - `db.py` - Database engine and session factory
   - `errors.py` - Exception handlers
   - `logging.py` - Structured logging configuration
   - `middleware.py` - Custom middleware (request ID, security headers, access logs, size limits)
   - `metrics.py` - Prometheus metrics setup

6. **Telegram** (`app/telegram/`) - Telegram bot integration
   - `bot.py` - TelegramBot wrapper managing lifecycle and handlers
   - `polling.py` - Development polling mode (alternative to webhooks)
   - Webhooks are configured in production/staging via `BACKEND_DOMAIN`

### Configuration

All configuration is centralized in `app.core.config.Settings`:
- Loads from `.env` or `../.env` files
- Strict validation with Pydantic
- Required vars: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`
- Environment-specific behavior controlled by `APP_ENV` (local/test/staging/production)
- CORS origins are automatically configured:
  - Always includes `https://webapp.telegram.org`
  - Localhost origins via `BACKEND_CORS_ORIGINS` only honored in local/test environments
  - Production origins via `PRODUCTION_APP_ORIGIN`

### Database Strategy

- **Production**: PostgreSQL with asyncpg driver
- **Tests**: SQLite in-memory with aiosqlite (see `tests/conftest.py`)
- All operations use SQLAlchemy async sessions
- Models use soft deletes (set `deleted=True` instead of removing rows)
- Alembic migrations auto-discover models through `app.models.base.Base.metadata`

### Telegram Bot Integration

The bot supports two modes:
1. **Webhooks** (production/staging): Configured automatically on startup if `BACKEND_DOMAIN` is set
2. **Polling** (local/test): Use `app.telegram.polling` module for development

Bot lifecycle is managed in `app/main.py`:
- `startup` event calls `telegram_bot.sync_webhook()`
- `shutdown` event calls `telegram_bot.shutdown()`

### Testing Patterns

Tests use pytest with asyncio support:
- Fixtures in `tests/conftest.py` provide in-memory SQLite sessions
- Each test gets a fresh database via `db_session` fixture
- Use `pytest-asyncio` for async test functions
- Assertion checks are allowed in tests (ruff ignores S101 for test files)

### Middleware Stack (applied in order)

1. `RequestIDMiddleware` - Adds `X-Request-ID` to all requests/responses
2. `RequestSizeLimitMiddleware` - Enforces `MAX_REQUEST_BYTES` (default 1 MiB)
3. `AccessLogMiddleware` - Structured access logging
4. `SecurityHeadersMiddleware` - Security headers (HSTS in staging/production)
5. `CORSMiddleware` - CORS with configured origins

## Important Patterns

### КРИТИЧНО: Проверка документации перед реализацией

**Перед написанием любого кода:**
1. Откройте соответствующий файл из `../docs/`
2. Убедитесь, что ваша реализация соответствует спецификации
3. Проверьте связанные документы (например, при работе с API проверьте и `backend-api.md`, и `backend-database.md`)

**При несоответствии кода и документации** - код неправильный и должен быть исправлен.

### Dependency Injection Pattern
```python
# In routes
async def endpoint(session: AsyncSession = Depends(get_session)):
    repository = UserRepository(session)
    service = UserService(repository)
    return await service.register_user(...)
```

### Repository Pattern
```python
# Repositories handle all database queries
class UserRepository(BaseRepository[User]):
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id, User.deleted == False)
        )
        return result.scalar_one_or_none()
```

### Alembic Migrations
- Alembic uses `settings.database_url` dynamically from environment
- The dummy URL in `alembic.ini` is overridden in `alembic/env.py`
- Always import all models in `app/models/__init__.py` for autogenerate to work
- Migrations run automatically on container startup via `docker-entrypoint.sh`

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/backend-deploy.yml`):
1. **Tests**: Runs pytest with PostgreSQL and Redis services, requires 80% coverage
2. **Build**: Builds Docker image and pushes to GHCR (main branch only)
3. **Deploy**: Deploys to server via SSH, pulls images, and restarts stack (main branch only)
4. **Notifications**: Telegram notifications on success/failure (if configured)

## Key Dependencies

- **FastAPI** - Web framework
- **SQLAlchemy 2.0** - Async ORM
- **Alembic** - Database migrations
- **Pydantic** - Validation and settings
- **python-telegram-bot** - Telegram Bot API
- **OpenAI** - LLM integration
- **Redis** - Caching and session storage
- **Ruff** - Fast Python linter and formatter (replaces black, isort, flake8)
- **mypy** - Static type checking (strict mode)

## Coding Standards

### Code Style Requirements (from docs/development-guidelines.md)

- Python 3.11+ with strict type hints
- Line length: 100 characters
- Use async/await for all I/O operations
- All functions must have type annotations (enforced by mypy strict mode)
- Use `from __future__ import annotations` for forward references
- Prefer explicit over implicit (e.g., specify nullable columns)

### File Size and Responsibility Limits

**Принцип малых файлов** (из `docs/development-guidelines.md`):

- **Максимум 300 строк на файл** (исключение: модели данных до 400 строк)
- **Один класс на файл** (исключение: тесно связанные классы типа Request/Response models)
- **Максимум 5-7 публичных методов на класс**
- **Методы до 50 строк** (сложные методы разбивать на приватные подметоды)

**Признаки что файл нужно разделить:**
- Импорты занимают > 20 строк
- Более 3 уровней вложенности условий/циклов
- Дублирование кода внутри файла
- Сложность тестирования (мокирование > 5 зависимостей)

### Test Coverage Requirements

**ОБЯЗАТЕЛЬНЫЕ требования** (из `docs/development-guidelines.md`):

- **Минимум 80%** общего покрытия (enforced by CI)
- **100%** покрытие критичных модулей:
  - Authentication (auth_service.py)
  - Payment processing (subscription_service.py)
  - Data access layer (repositories)
- **Все edge cases** должны быть покрыты тестами

### Documentation in Code

**Каждый файл должен содержать:**
1. Заголовок с описанием модуля (что делает, зачем нужен)
2. Описание публичного API (параметры, возвращаемые значения, исключения)
3. TODO markers для известных ограничений

**Комментарии должны объяснять "ПОЧЕМУ", а не "ЧТО"**
