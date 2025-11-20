# Repository Guidelines

## Project Structure & Module Organization
- `docs/` — норматив, содержит архитектуру, API и процессы; код обязан ей соответствовать.
- `backend/app/` — FastAPI backend, разложенный по слоям: `api` (роуты), `core` (config, logging), `models`, `repositories`, `services`.
- `backend/tests/` — pytest/pytest-asyncio suite; каждую новую фичу сопровождаем тестами здесь.

## Build, Test, and Development Commands
```bash
cd backend
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
ruff check app           # линтинг (fixable via ruff --fix)
black --check app        # форматирование
mypy app                 # строгая проверка типов
pytest --cov=app --cov-fail-under=85  # тесты и целевой порог покрытия
```
Когда появится приложение, используем `uvicorn app.main:app --reload` для локального прогона и `alembic upgrade head` перед стартом, чтобы схемы совпадали.
- Перед сдачей работы агент обязательно запускает те же проверки, что и прекоммит (`pre-commit run --all-files` или эквивалентные команды: end-of-file/trailing-whitespace, `black`, `isort`, `ruff`, `mypy` на `backend/app`) и исправляет замечания до зелёного статуса.

## Coding Style & Naming Conventions
- Python 3.11+, 4‑пробельные отступы; максимум 300 строк на файл (см. `docs/development-guidelines.md`).
- Слои не пересекаются: API → services → repositories → models.
- Инструменты: Black (LL=100), isort (profile=black), Ruff (E,F,I,W,B,ANN,S,C90), mypy `strict`.
- Переменные окружения через `pydantic-settings`; никаких секретов вне `.env` (см. `.env.example`).

## Testing Guidelines
- Фреймворк: `pytest` + `pytest-asyncio`; покрытие ≥85 % глобально и 100 % для критичных модулей (auth, repositories).
- Имена тестов описательные: `test_<feature>_<behavior>`; файлы зеркалят исходные модульные пути.
- Добавляйте интеграционные проверки для health/check endpoints и репозиториев; запускайте `pytest --cov` до каждого PR.

## Commit & Pull Request Guidelines
- **Commits:** Conventional Commits `type(scope): subject` (`feat(api): add health endpoint`). Subject ≤72 символов, повелительное наклонение, body объясняет «что/почему». Breaking changes описываем отдельным блоком.
- **Branches:** `feature/LANG-123-short-title`, `bugfix/...`, `hotfix/...`; создаём от `develop` (или `main` для hotfix).
- **Pull Requests:** шаблон из `docs/development-guidelines.md` — описание, связанные задачи, чеклист, шаги тестирования, медиа. Требуются зелёные CI, обновлённые docs/tests и минимум два approval. После merge ветку удаляем.

## Security & Configuration Tips
- Всегда синхронизируйтесь с `docs/deployment.md` перед изменением окружений. `.env` не коммитим; для локальной работы копируйте `.env.example`.
- CORS ограничен `https://webapp.telegram.org` плюс `PRODUCTION_APP_ORIGIN`; `BACKEND_CORS_ORIGINS` учитывается только при `APP_ENV=local/test` и служит для whitelisting `http://localhost:<port>`.
- Публичный backend-домен задаётся через `BACKEND_DOMAIN` (без схемы). Он используется nginx-proxy/Let's Encrypt и для построения webhook URL (`https://<BACKEND_DOMAIN>/telegram-webhook/<bot_token>`).
- Логи и middleware должны обогащать `request_id`, но не содержать токенов или персональных данных.

## README & Docs Sync Policy (обязательно)
- После любых изменений, влияющих на запуск, API/контракты, структуру проекта, команды разработки/деплоя, переменные окружения или quality‑гейты — обновляйте `README.md` в том же PR.
- Минимальный объём обновления README:
  - Разделы «Что уже готово», «Быстрый старт», «Структура репозитория», «Технологический стек», «Definition of Done», «Roadmap» должны отражать текущее состояние.
  - Команды для локального запуска/проверок/деплоя — копируемы и актуальны (с учётом Makefile/scripts и Docker Compose).
  - Ссылка на соответствующие документы в `docs/` (архитектура, API, БД, CI/CD, деплой) — проверены и ведут на релевантные файлы.
- Когда меняются переменные окружения, добавляйте/обновляйте их в `.env.example` и отражайте в README (раздел «Быстрый старт» / «Environment»).
- Если меняется публичный контракт API, кратко отметьте ключевые эндпоинты/изменения в README (с отсылкой на `docs/backend-api.md`).

## MCP / Context7 Policy
- При работе с библиотеками обязательно используйте MCP Context7: сначала `resolve-library-id`, затем `get-library-docs` по нужной теме. Не допускается «угадывать» API/паттерны без запроса актуальной документации через эти методы.

### Чеклист синхронизации README для каждого PR
- [ ] Обновлён «Что уже готово» под текущий прогресс
- [ ] Обновлён «Быстрый старт» (команды, prereqs, env)
- [ ] Обновлена «Структура репозитория» при изменении модулей/папок
- [ ] Обновлён «Технологический стек» при смене библиотек/инструментов
- [ ] Обновлён «Definition of Done» и quality‑гейты, если менялись
- [ ] Обновлён «Roadmap (из to‑do.md)» либо ссылка подтверждена актуальной
- [ ] Ссылки на `docs/*` ведут на актуальные разделы
