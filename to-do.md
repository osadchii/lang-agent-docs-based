# Дорожная карта имплементации (to-do)

Назначение: разбить реализацию на небольшие, независимые задачи, которые можно брать по одной. Все задачи строго следуют нашей документации в `docs/` и не добавляют новых фичей.

Общие правила выполнения задач:
- Перед началом задачи перечитать релевантные документы в `docs/` (см. ссылки в каждом разделе).
- Держать изменения маленькими и изолированными. Покрывать критичные пути тестами.
- Соблюдать `docs/development-guidelines.md` (стиль, структура, тесты, лимиты файлов).

---

## 0. Подготовка репозитория (foundation)
Docs: docs/architecture.md, docs/deployment.md, docs/development-guidelines.md

- [ ] Создать структуру каталогов `backend/`, `frontend/`, `.github/workflows/`, `infra/` (если потребуется позже).
- [ ] Backend: сгенерировать базовый проект FastAPI (`app/main.py`, `app/api/routers.py`, `app/core/config.py`, `app/core/logging.py`).
- [ ] Backend: добавить `requirements.txt` (FastAPI, Uvicorn, SQLAlchemy[async], Alembic, psycopg, python-telegram-bot, redis, pydantic, httpx/requests, openai==1.6.1, python-jose/jwt и др. строго по необходимости из docs).
- [ ] Backend: реализовать `/health` (GET) согласно `docs/backend-api.md` (пока возвращать статический 200 + версию из конфига).
- [ ] Backend: включить CORS под Telegram WebApp: `https://webapp.telegram.org` (см. `docs/backend-api.md`).
- [ ] Docker: добавить `backend/Dockerfile` по `docs/deployment.md`.
- [ ] Docker: добавить `docker-compose.dev.yml` из `docs/deployment.md` (PostgreSQL + Redis).
- [ ] Репозиторные мета-файлы: `.editorconfig`, `.gitignore`, `.env.example` (без секретов, список переменных из `docs/deployment.md`).
- [ ] Настроить форматирование/линтинг backend: Black, isort, Ruff, mypy (см. `docs/development-guidelines.md`).

---

## 1. База данных и миграции
Docs: docs/backend-database.md

- [ ] Alembic: инициализация, базовый `env.py`, `alembic.ini`.
- [ ] Миграция 000: функция-триггер `update_updated_at_column()` (общая для всех таблиц).
- [ ] Миграция 001: `users` (+ индексы, триггеры) как в спецификации.
- [ ] Миграция 002: `language_profiles` (+ ограничения и уникальность активного профиля).
- [ ] Миграция 003: `decks` (+ unique active per profile, счетчики).
- [ ] Миграция 004: `cards` (все поля SRS, индексы, soft delete).
- [ ] Миграция 005: `topics` (личные/групповые, активная тема, soft delete).
- [ ] Миграция 006: `conversation_history` (хранение истории диалога с токенами).
- [ ] Миграция 007: `exercise_history` (результаты, время, подсказки).
- [ ] Миграция 008: `groups`, `group_members`, `group_materials` (если выделено).
- [ ] Миграция 009: `subscriptions` (stripe ids, статусы, периоды).
- [ ] Денормализация: триггеры обновления счетчиков для колод при изменении карточек.

---

## 2. Конфигурация, безопасность и аутентификация
Docs: docs/backend-auth.md, docs/backend-api.md

- [ ] Конфигурация: загрузка переменных окружения (`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, `ENVIRONMENT`, JWT TTL и пр.).
- [ ] JWT утилиты: создание/проверка токена (HS256, TTL 30 минут).
- [ ] Валидация Telegram WebApp `initData` (HMAC-SHA256) строго по алгоритму из `docs/backend-auth.md`.
- [ ] Endpoint `POST /api/auth/validate` (возвращает `user`, `token`, `expires_at`).
- [ ] Auth dependency: извлечение `user` из заголовка `Authorization: Bearer <token>`.
- [ ] CORS и заголовки безопасности (минимально необходимые под Mini App + Bot webhook).

---

## 3. Rate limiting и лимиты тарифов
Docs: docs/backend-api.md, docs/backend-subscriptions.md

- [ ] Redis: инициализация клиента, пространство ключей.
- [ ] Пер-пользовательские лимиты: сообщения LLM/день, упражнения/день, карточки (free/premium).
- [ ] Глобальные лимиты: per-IP и per-user по `docs/backend-api.md` (заголовки `X-RateLimit-*`).
- [ ] Ошибки при превышении лимитов (формат ответа из спецификации).

---

## 4. Пользователи и профили
Docs: docs/backend-api.md (Users, Language Profiles), docs/use-cases.md (UC-0)

- [ ] `GET /api/users/me` (возвращает статусы лимитов и подписки).
- [ ] `PATCH /api/users/me` (ограниченные поля: имя/фамилия и т.п.).
- [ ] `GET /api/profiles` (список профилей пользователя).
- [ ] `POST /api/profiles` (создание с проверкой лимитов free/premium и уникальности языка).
- [ ] `GET /api/profiles/{id}`.
- [ ] `PATCH /api/profiles/{id}` (нельзя менять `language`).
- [ ] `DELETE /api/profiles/{id}` (soft delete, запрет удаления последнего профиля).
- [ ] `POST /api/profiles/{id}/activate` (единственный активный профиль).

---

## 5. Колоды и карточки (SRS)
Docs: docs/backend-flashcards.md, docs/backend-api.md (Decks, Cards), docs/use-cases.md (UC-2, UC-3)

- [ ] `GET /api/decks` (включая групповые при `include_group=true`).
- [ ] `POST /api/decks` / `GET /api/decks/{id}` / `PATCH` / `DELETE` / `POST /activate`.
- [ ] `GET /api/cards` (фильтры: deck, status, search, пагинация).
- [ ] `POST /api/cards` (одна/список слов) с генерацией через LLM и проверкой дубликатов по лемме.
- [ ] `GET /api/cards/{id}` / `DELETE /api/cards/{id}` (soft delete).
- [ ] `POST /api/cards/rate` (оценка: know/repeat/dont_know) — расчёт интервала по упрощенному SM-2.
- [ ] `GET /api/cards/next` (выбор следующей карточки: просроченные → новые).
- [ ] Юнит-тесты для расчёта интервалов и выбора карточек.

---

## 6. Темы и упражнения
Docs: docs/backend-exercises.md, docs/backend-api.md (Topics, Exercises), docs/use-cases.md (UC-4)

- [ ] `GET /api/topics` / `POST /api/topics` / `GET /{id}` / `PATCH` / `DELETE`.
- [ ] `POST /api/topics/{id}/activate` (единственная активная тема).
- [ ] `POST /api/topics/suggest` (рекомендации от LLM).
- [ ] `POST /api/exercises/generate` (free_text/multiple_choice) по активной теме и уровню.
- [ ] `POST /api/exercises/{id}/submit` (проверка ответа через LLM, сохранение истории).
- [ ] Учёт дневного лимита упражнений (free/premium) и попадание в общий LLM лимит.

---

## 7. Подписки и биллинг (Stripe)
Docs: docs/backend-subscriptions.md, docs/backend-api.md (/subscriptions)

- [ ] `GET /api/subscriptions/status` (trial/active/expired, лимиты).
- [ ] `POST /api/subscriptions/create-checkout` (Stripe Checkout, выбор плана month/year).
- [ ] `POST /api/subscriptions/webhook` (обработка событий: checkout.session.completed, invoice.paid, invoice.payment_failed, customer.subscription.updated/deleted).
- [ ] `POST /api/subscriptions/cancel` (отмена автопродления, статус до конца периода).
- [ ] Обновление `users.is_premium`, `premium_expires_at` по событиям Stripe.

---

## 8. LLM сервис и промпты
Docs: docs/backend-llm.md, docs/backend-bot-responses.md

- [ ] Клиент OpenAI: единая обёртка, ретраи, таймауты, телеметрия токенов (счётчики).
- [ ] Структура `backend/prompts/` как в `docs/backend-llm.md` (system/cards/exercises/dialog/utils; Jinja2).
- [ ] `detect_intent`, `process_user_message` (история: 20 сообщений или 24 часа, до 8000 токенов).
- [ ] Генерация карточки: `generate_card_content` (+ `get_lemma`, проверка дубликатов).
- [ ] Генерация/проверка упражнения: `generate_exercise`, `check_exercise_answer`.
- [ ] Формирование ответов бота по `docs/backend-bot-responses.md` (Markdown, инлайн-кнопки, ветвления).

---

## 9. Телеграм-бот (Bot + webhook)
Docs: docs/backend-telegram.md

- [ ] Зависимость `python-telegram-bot[webhooks]` (версия 20+), асинхронная конфигурация.
- [ ] Входная точка вебхука: `POST /telegram-webhook/{bot_token}` (роутер FastAPI).
- [ ] Регистрация хендлеров: команды `/start`, `/help`, `/profile`, `/app`, `/stats`, `/card`, `/decks`, `/exercise`, `/topics`.
- [ ] Диалоговые сообщения: обработка текстов — либо диалог с LLM, либо ответы на упражнения.
- [ ] CallbackQuery: кнопки (переключение профиля/колоды/темы, flip карточки, оценка, next и т.п.).
- [ ] Старт/онбординг: создание пользователя, предложение открыть Mini App.
- [ ] Лимиты сообщений (бесплатные/премиум) и кнопка апгрейда.
- [ ] Сообщения с карточками/упражнениями: форматирование и сценарии из `docs/backend-bot-responses.md`.
- [ ] Dev: long-polling; Prod: webhook (URL из `TELEGRAM_WEBHOOK_URL`).

---

## 10. Frontend (React Mini App)
Docs: docs/frontend-structure.md, docs/frontend-screens.md, docs/frontend-navigation.md, docs/backend-api.md

- [ ] Scaffold Vite + React + TypeScript, строгий TS, ESLint + Prettier.
- [ ] Интеграция `@twa-dev/sdk` (+ типы), получение `initData`.
- [ ] Auth flow: `POST /api/auth/validate`, хранение JWT, обновление по истечению.
- [ ] API слой: Axios клиент с интерцепторами, React Query, хуки (`useCards`, `useExercises`, ...).
- [ ] Zustand стор: `auth`, `profile`, `ui`, `settings`.
- [ ] Роутер и каркас страниц согласно структуре (RootLayout, PracticeLayout, ErrorBoundary).
- [ ] Онбординг (5 шагов) — создание профиля через API.
- [ ] Главная (Home): активный профиль, краткая статистика, CTA.
- [ ] Практика/Карточки: списки колод, детали колоды, study session (взаимодействие с `cards/next`, `cards/rate`).
- [ ] Практика/Упражнения: генерация/отправка ответов (`/exercises/generate`, `/submit`).
- [ ] Профиль: настройки интерфейса, языковые профили (CRUD), статистика/стрик.
- [ ] Группы: список/детали, управление участниками (минимальный CRUD, без расширений).
- [ ] Подписка: страница Premium, вызов `/subscriptions/create-checkout`, открытие `checkout_url`.
- [ ] UI-компоненты: Button, Input, Card, BottomNav, Modal, Toast, Skeleton; дизайн токены/темы.
- [ ] Тесты: Vitest + RTL, smoke-тесты ключевых страниц, хуков и API-слоя.

---

## 11. CI/CD и деплой
Docs: docs/ci-cd.md, docs/deployment.md

- [ ] GitHub Actions: `backend-test.yml` (линт, типы, тесты с Postgres/Redis сервисами).
- [ ] GitHub Actions: `backend-deploy.yml` (buildx → Docker Hub → копирование `docker-compose.yml` → миграции → апдейт контейнеров → health-check).
- [ ] GitHub Actions: `frontend-test.yml` (линт, формат, типы, тесты, build).
- [ ] GitHub Actions: `frontend-deploy.yml` (build → upload `dist` → reload Nginx).
- [ ] Подготовка `docker-compose.yml` (prod) под backend+db+redis.
- [ ] Подготовка Nginx-конфига (reverse proxy для `/api`, раздача `frontend/dist`).
- [ ] Создать и заполнить `.env` на сервере вручную (переменные из `docs/deployment.md`).

---

## 12. Мониторинг, логирование, качество
Docs: docs/deployment.md (Monitoring), docs/development-guidelines.md

- [ ] Структурированное логирование backend (уровни, корреляция запросов).
- [ ] Sentry интеграция (ошибки backend; опционально фронтенд) — только если указан DSN.
- [ ] Метрики: базовые (latency, rate, error) через middleware и логи (интеграция Prometheus — по мере необходимости).
- [ ] Ответы API: корректные коды ошибок/сообщения + `X-RateLimit-*` заголовки.
- [ ] Минимальные E2E сценарии (Playwright) для критичных флоу Mini App (опционально).

---

## 13. Проверка соответствия use-cases
Docs: docs/use-cases.md, docs/use-cases-questions.md

- [ ] UC-0: Онбординг, создание и активация профиля, язык интерфейса — через бот/Mini App.
- [ ] UC-1: Диалог с помощником, история диалога, лимиты сообщений, кнопки быстрых действий.
- [ ] UC-2: Добавление слов (текстом/кнопкой), проверка дубликатов, привязка к активной колоде.
- [ ] UC-3: Изучение карточек (бот и Mini App), переворот, оценка, SM-2 интервалы.
- [ ] UC-4: Темы и упражнения (генерация, проверка, подсказки, лимиты), история результатов.

---

## Мини‑порядок реализации (предлагаемый)

1) Foundation: каркас backend + `/health`, Docker/dev compose, линтеры.
2) DB: Alembic + миграции (users → profiles → decks/cards → topics → history → groups → subscriptions).
3) Auth: `POST /api/auth/validate` + JWT + CORS.
4) Users/Profiles: CRUD + лимиты.
5) Flashcards: Decks/Cards + SRS + тесты.
6) LLM: клиент + промпты + генерация карточек.
7) Exercises/Topics: генерация/проверка + история.
8) Telegram Bot: команды, коллбеки, формат ответов, лимиты.
9) Subscriptions: статус, checkout, webhook, отмена.
10) Frontend: scaffold, auth, onboarding, practice, profile, subscription.
11) CI/CD + Deploy: workflows, docker-compose, nginx.
12) Мониторинг/логирование + E2E smoke.

Примечание: если по ходу реализации обнаружится расхождение между кодом и `docs/`, приоритет у документации. Обновлять код/задачи синхронно с документами.

