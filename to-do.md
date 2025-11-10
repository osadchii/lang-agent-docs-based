# To‑Do: Пошаговый план имплементации

Назначение: последовательный план работ для вывода минимально жизнеспособного продукта (бот отвечает на вопросы) с ранним CI/CD и деплоем. Все задачи выполняются в строгом соответствии с документацией в `docs/` (источник правды). Любые отклонения — обновить код и соответствующие документы в одном PR.

## Definition of Done (для каждого шага)
- Обновлены релевантные документы в `docs/`
- Качество кода: `black`, `isort`, `ruff`, `mypy` без ошибок
- Тесты проходят, покрытие backend ≥85% (критичные модули — 100%)
- Pipeline CI зелёный; при необходимости обновлён деплой
- Нет секретов в репозитории; конфиги через `.env` и `Settings`
- При закрытии каждой задачи обязательно отмечаем чекбокс в этом списке.

## Этап A. Инициализация проекта (Backend + общая структура)
- [x] **1) Скелет репозитория**
   - Создать структуру: `backend/app/{api,core,services,models,repositories}`; `backend/tests/`
   - Добавить `backend/pyproject.toml` (ruff, black, isort, mypy), `backend/requirements.txt`, `.editorconfig`, `.gitignore`, `.env.example`
   - Настроить `app.core.config.Settings` (строгая типизация, чтение `.env`)
   - Acceptance: локальный импорт/запуск без ошибок

- [x] **2) FastAPI приложение и health endpoint**
   - `app/main.py` с FastAPI, роут `/health` (см. `docs/backend-api.md` → Health Check)
   - Подготовить CORS (строго: `https://webapp.telegram.org` + домен продакшена из ENV)
   - Acceptance: `uvicorn app.main:app --reload` и `GET /health` → 200 JSON (без внешних проверок пока)

- [x] **3) Логирование (структурированное)**
   - `app/core/logging.py`: JSON‑логи, уровень из ENV, кореляционный `request_id`
   - Встроить middleware для `request_id` и access‑логов
   - Acceptance: логи в stdout в JSON, поля: level, ts, method, path, status, request_id

- [x] **4) База данных и миграции**
   - PostgreSQL (SQLAlchemy 2.x, async) + Alembic
   - Сразу добавить модели и миграции для: `users`, `conversation_history` (см. `docs/backend-database.md`)
   - Сервис и репозитории: `UserRepository`, `ConversationRepository`
   - Acceptance: `alembic upgrade head` применяет миграции, базовые CRUD тесты зелёные

- [x] **5) Локальное окружение**
   - `docker-compose.local.yml`: `postgres`, `redis` (см. `docs/deployment.md`), сети/тома
   - Makefile или `scripts/` с командами: `local-up`, `local-down`, `test`, `lint`
   - Acceptance: `docker-compose -f docker-compose.local.yml up -d` поднимает сервисы; backend коннектится к БД

- [ ] **6) Базовые тесты и quality gates**
   - Pytest конфиг, smoke‑тест `/health`, репозитории (users, conversation)
   - Настроить `pytest --cov=app --cov-fail-under=85`
   - Acceptance: локальный запуск тестов зелёный, покрытие ≥85%

## Этап B. CI/CD и деплой (сразу после скелета)
- [ ] **7) CI: backend tests**
   - Добавить `.github/workflows/backend-test.yml` (см. `docs/ci-cd.md`), сервисы Postgres/Redis в job
   - Шаги: линтеры, типы, тесты, coverage upload (опц.)
   - Acceptance: pipeline успешно проходит на любом пуше в ветки

- [ ] **8) Образы и прод‑compose**
   - `backend/Dockerfile` (см. `docs/deployment.md`), корневой `docker-compose.yml` для prod
   - Healthcheck контейнера и зависимостей; команда старта с Alembic upgrade перед `uvicorn`
   - Acceptance: локальная сборка образа, `docker-compose up -d backend db redis` работает

- [ ] **9) CI: backend deploy (main)**
   - `.github/workflows/backend-deploy.yml`: buildx, push в Docker Hub, SCP `docker-compose.yml`, SSH деплой, health‑проверка
   - Подготовить список GitHub Secrets и чек‑лист подготовки сервера (см. `docs/ci-cd.md`)
   - Acceptance: пуш в `main` приводит к успешному деплою и `GET /health` → 200 на сервере

## Этап C. Обсервабилити (локально и/или прод)
- [ ] **10) Loki + Grafana (локально и опционально на проде)**
   - В `docker-compose.local.yml` добавить `loki`, `grafana`, `promtail` (или docker‑лог драйвер для Loki)
   - Для продакшена — по желанию включить эти сервисы в `docker-compose.yml` или отдельный `docker-compose.observability.yml`
   - Провиженинг Grafana (папка `infra/grafana/`), базовая дашборда: RPS, p95 latency, ошибки, 4xx/5xx, top endpoints
   - Acceptance: логи backend попадают в Loki; дашборда показывает метрики/логи

- [ ] **11) Метрики и трассировки (минимум)**
   - Добавить Prometheus‑совместимые метрики через `prometheus_fastapi_instrumentator`
   - Привязка `request_id` к логам/ошибкам; базовые алерты (если Grafana/Prometheus есть на проде)
   - Acceptance: `/metrics` доступен локально; при включении на проде — графики в Grafana

## Этап D. Безопасность и конфигурация
- [ ] **12) Settings и секреты**
   - Полный список переменных окружения (см. `docs/deployment.md`), `.env.example` с комментариями
   - JWT параметры, CORS, токены провайдеров, Redis URL, DB URL
   - Acceptance: приложение не стартует без обязательных переменных (чёткие ошибки)

- [ ] **13) CORS и заголовки**
   - Разрешить только `https://webapp.telegram.org` и прод‑домен; для локального фронтенда — whitelisting `http://localhost:*` через ENV
   - Добавить security middleware (HSTS в Nginx), ограничить размер запросов
   - Acceptance: preflight проходит только для допустимых origin

## Этап E. Интеграция с Telegram Bot (базовый диалог)
- [ ] **14) Бот и вебхук**
   - Библиотека `python-telegram-bot` 20+; эндпоинт `POST /telegram-webhook/{bot_token}` в FastAPI (см. `docs/architecture.md`, `docs/backend-telegram.md`)
   - Старт: setWebhook (prod) / polling (dev); обработчик `/start`
   - Acceptance: сообщение в бота достигает backend handler (логи, 200), бот отвечает "Привет!"

- [ ] **15) Пользователь и онбординг**
   - На первое сообщение: `get_or_create_user(telegram_id, ...)` в БД (таблица `users`)
   - Логика онбординга: зафиксировать минимум (язык интерфейса из Telegram)
   - Acceptance: запись пользователя создаётся, повторный вход — обновление `last_activity`

- [ ] **16) Диалог с LLM (минимум)**
   - Сервис `LLMService` (OpenAI SDK) + `DialogService`
   - System prompt из `docs/backend-llm.md` (минимальная версия), безопасные таймауты
   - ВАЖНО: сохранять каждое сообщение (user/assistant) в `conversation_history` сразу (никакого in‑memory)
   - Acceptance: бот отвечает на текстовые вопросы, история пишется в БД

## Этап F. LLM провайдер и промпты
- [ ] **17) Адаптер LLM**
   - Обёртка над OpenAI: инициализация клиента, retries, таймауты, логирование токенов
   - Конфиг модели/температуры из ENV; фича‑флаг альтернативного провайдера (на будущее)
   - Acceptance: юнит‑тесты адаптера (моки), стабильная обработка ошибок API

- [ ] **18) Промпты и контекст**
   - Структура `backend/prompts/` как в `docs/backend-llm.md`; базовый `system/teacher.txt`
   - Контекст: последние N сообщений пользователя (из БД) для ответа
   - Acceptance: ответы учитывают историю, промпт рендерится корректно

## Этап G. Mini App (Frontend) — ранний скелет
- [ ] **19) Бутстрап фронтенда**
   - Vite + React + TS, SDK `@twa-dev/sdk`; страницы: Home (плейсхолдер), Error
   - Интеграция Telegram WebApp initData (получение на старте)
   - Acceptance: билд/дев‑сервер, отрисовывается стартовый экран

- [ ] **20) Auth через initData**
   - Эндпоинт `/api/auth/validate` (см. `docs/backend-api.md`, `docs/backend-auth.md`) — валидация HMAC, выдача JWT
   - Frontend сохраняет JWT (memory) и использует в запросах (Axios interceptors)
   - Acceptance: успешная валидация initData, получение `user`, `token`

- [ ] **21) Минимальный экран «Задать вопрос»**
   - Простая форма: ввод текста → `POST /api/sessions/chat` (или `/api/dialog/ask`) на backend, который использует тот же `DialogService`
   - Список последних сообщений (из `/api/dialog/history`), пагинация простая
   - Acceptance: пользователь видит ответ ИИ прямо в Mini App; история приходит из БД

- [ ] **22) CI фронтенда и деплой**
   - Workflows: `frontend-test.yml`, `frontend-deploy.yml` (см. `docs/ci-cd.md`)
   - Prod hosting: выкладка `frontend/dist/` на сервер, Nginx конфиг (см. `docs/deployment.md`)
   - Acceptance: пуш в `main` деплоит фронтенд; страница грузится с сервера

## Этап H. Расширение базовой функциональности (после MVP)
- [ ] **23) Профили (минимум)**
   - Таблицы/эндпоинты `language_profiles` (см. `docs/backend-database.md`, `docs/backend-api.md`)
   - В Mini App: создать/активировать профиль, переключение в боте
   - Acceptance: 1 активный профиль/пользователь, валидации уровня CEFR

- [ ] **24) Карточки (минимум)**
   - Таблицы/эндпоинты `decks`, `cards`, `card_reviews` (минимальный SRS)
   - В боте: команды `/card`, `/decks` (простые кнопки); в App — список колод и добавление карточки
   - Acceptance: создание карточки сохраняется в БД; выбор следующей карточки отдаёт корректный объект

- [ ] **25) Упражнения (минимум)**
   - Таблицы/эндпоинты `topics`, `exercise_history`; генерация задания через LLM по активной теме
   - В App: запуск сессии 5–10 заданий, фиксация результата
   - Acceptance: выполненные упражнения пишутся в `exercise_history`, отображается базовая статистика темы

- [ ] **26) История и статистика**
   - Агрегаты по карточкам/упр.; простые метрики в App
   - Acceptance: страницы статистики отдают корректные данные, дашборды понятны

## Этап I. Последние фичи (монетизация, лимиты, группы)
- [ ] **27) Лимиты и тарифы (скелет)**
   - Rate limiting (per‑user/глобальные) через Redis, заголовки `X-RateLimit-*` (см. `docs/backend-api.md`)
   - Планировщик сброса суточных счетчиков
   - Acceptance: превышение лимитов возвращает стандартизированную ошибку, заголовки корректны

- [ ] **28) Подписки (Stripe)**
   - Схема `subscriptions`, обработка webhooks (`checkout.session.completed`, `invoice.paid`, и т.п.)
   - Эндпоинты для создания checkout‑сессии, отображение статуса в App
   - Acceptance: успешный платёж меняет статус подписки; флаги в JWT отражают премиум

- [ ] **29) Группы**
   - Сущности групп, шаринг колод/тем, роли владелец/участник
   - Правила доступа в API/боте, базовые экраны в App
   - Acceptance: создание группы, приглашение, доступ к общим материалам

## Нефункциональные требования и оговорки
- Хранение данных «сразу правильно»: история диалогов, карточки, упражнения — только в БД, не in‑memory
- Слой сервисов не зависит от фреймворка; обработчики (бот/REST) только валидируют и делегируют в сервисы
- Производительность: таймауты LLM, очереди/ретраи; кэш Redis для горячих данных (позже)
- Безопасность: не доверяем `user_id` из клиента; для Mini App — только `initData` с HMAC
- Документация — закон: при изменениях обновлять `docs/*` в том же PR

## Ранние демонстрации (контрольные точки)
- A2: локальный `/health` 200, миграции применяются
- B9: автодеплой из `main`, `/health` 200 на прод‑сервере
- E16: бот отвечает на вопросы, история в БД
- G21: Mini App задаёт вопрос и получает ответ, история из БД

## Следующие шаги прямо сейчас
1) Выполнить Этап A (1–6) в одном PR `feat(backend): bootstrap app + db + health`
2) Сразу за ним Этап B (7–9) — настроить CI/CD и проверить автодеплой на сервер
3) Затем Этап C (10–11) — логи/дашборды в dev для удобной отладки
4) Параллельно начать Этап E/F (14–18) — минимальный бот + LLM
5) После ответа бота — Этап G (19–22) для раннего экрана Mini App
