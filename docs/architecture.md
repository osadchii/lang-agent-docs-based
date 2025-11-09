# Архитектура системы

## Общая схема

Система построена как **монолитное backend приложение** с разделением на Backend (Python), Frontend (React Mini App) и внешние сервисы.

**Backend** - это **одно приложение (FastAPI)** с двумя точками входа:
1. **Bot Handler** (`POST /telegram-webhook/{bot_token}`) - обрабатывает запросы от Telegram Bot API
2. **REST API** (`/api/*`) - обрабатывает запросы от Mini App

Оба используют одни и те же бизнес-сервисы, базу данных и инфраструктуру.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Telegram Platform                        │
│  ┌──────────────────┐                  ┌───────────────────┐    │
│  │  Telegram Bot    │                  │  Telegram Mini    │    │
│  │   (Chat UI)      │◄─────────────────┤      App          │    │
│  └────────┬─────────┘                  └─────────┬─────────┘    │
│           │                                       │              │
└───────────┼───────────────────────────────────────┼──────────────┘
            │                                       │
            │ Telegram Bot API                      │ HTTPS/REST
            │ (Webhooks/Long Polling)               │
            │                                       │
┌───────────▼───────────────────────────────────────▼──────────────┐
│                        Backend (Python)                           │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    API Gateway / Router                     │  │
│  │               (FastAPI / Flask / Django)                    │  │
│  └──────────┬────────────────────────────────┬─────────────────┘  │
│             │                                │                    │
│  ┌──────────▼──────────┐        ┌──────────▼──────────┐         │
│  │   Bot Handler        │        │    REST API         │         │
│  │  (Telegram Updates)  │        │  (Mini App Client)  │         │
│  └──────────┬───────────┘        └──────────┬──────────┘         │
│             │                               │                    │
│  ┌──────────▼───────────────────────────────▼──────────┐         │
│  │              Business Logic Layer                    │         │
│  │                                                      │         │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │         │
│  │  │ User/Profile│  │  Flashcards   │  │ Exercises │  │         │
│  │  │   Service   │  │   Service     │  │  Service  │  │         │
│  │  └─────────────┘  └──────────────┘  └───────────┘  │         │
│  │                                                      │         │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │         │
│  │  │   Groups    │  │   LLM/AI     │  │   Stats   │  │         │
│  │  │   Service   │  │   Service    │  │  Service  │  │         │
│  │  └─────────────┘  └──────────────┘  └───────────┘  │         │
│  │                                                      │         │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │         │
│  │  │Subscription │  │    Media     │  │   Auth    │  │         │
│  │  │   Service   │  │   Service    │  │  Service  │  │         │
│  │  └─────────────┘  └──────────────┘  └───────────┘  │         │
│  └──────────────────────────┬───────────────────────────┘         │
│                             │                                     │
│  ┌──────────────────────────▼───────────────────────────┐         │
│  │                  Data Access Layer                    │         │
│  │            (SQLAlchemy ORM / Async Drivers)           │         │
│  └──────────────────────────┬───────────────────────────┘         │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              │ PostgreSQL Protocol
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                      Database (PostgreSQL)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Users   │ │ Profiles │ │  Cards   │ │  Groups  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Decks   │ │  Topics  │ │ Sessions │ │  Stats   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                       External Services                          │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │  OpenAI API    │  │  Stripe API    │  │ Tesseract OCR  │    │
│  │  (GPT-4.1,     │  │  (Payments)    │  │ (Text from img)│    │
│  │   Whisper)     │  │                │  │                │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐                         │
│  │    Redis       │  │   Sentry       │                         │
│  │  (Cache/Queue) │  │ (Monitoring)   │                         │
│  └────────────────┘  └────────────────┘                         │
└──────────────────────────────────────────────────────────────────┘
```

---

## Компоненты системы

### 1. Backend (Python)

#### 1.1. API Gateway / Router

**Архитектурное решение: Монолит**

Бот и API - это **одно приложение**, потому что:
- ✅ Общая бизнес-логика (Flashcards, LLM, Stats сервисы)
- ✅ Общая база данных (без дублирования данных)
- ✅ Проще развертывание и отладка
- ✅ Меньше накладных расходов (нет межсервисной коммуникации)
- ✅ Достаточно для большинства нагрузок (можно масштабировать горизонтально)

При необходимости в будущем можно разделить на микросервисы.

**Технологии:**
- **FastAPI** (рекомендуется) - async, быстрый, автоматическая OpenAPI документация
- Альтернатива: Flask + Flask-RESTX или Django REST Framework

**Функции:**
- Роутинг запросов от Bot Handler и Mini App
- Валидация входных данных (Pydantic models)
- Аутентификация и авторизация
- Rate limiting
- CORS для Mini App
- Логирование и мониторинг

**Структура приложения:**
```python
# main.py
from fastapi import FastAPI
from bot.handlers import setup_bot_webhook
from api.routes import router as api_router

app = FastAPI()

# Bot webhook endpoint
app.include_router(setup_bot_webhook(), prefix="/telegram-webhook")

# Mini App REST API
app.include_router(api_router, prefix="/api")
```

**Endpoints:**
```
Bot Handler:
  POST /telegram-webhook/{bot_token}  - Telegram webhook

Mini App REST API:
  GET  /api/users/me
  GET  /api/profiles
  POST /api/profiles
  GET  /api/cards
  POST /api/cards
  POST /api/sessions
  ...
```

---

#### 1.2. Bot Handler

**Функции:**
- Обработка Telegram Updates (messages, callbacks, inline queries)
- Парсинг команд (/start, /add_card, /stats, и т.д.)
- Управление состоянием диалога (FSM - Finite State Machine)
- Отправка сообщений и inline кнопок
- Обработка media (photos, voice messages)

**Технологии:**
- **python-telegram-bot** (PTB) 20+ - высокоуровневая библиотека
- Альтернатива: aiogram 3+ (async-first)

**Архитектура:**
```python
# Handlers по типам
- CommandHandler (/start, /help, /stats, etc.)
- MessageHandler (text messages, media)
- CallbackQueryHandler (inline button clicks)
- InlineQueryHandler (inline mode)

# Conversation Handler для multi-step flows
- Onboarding flow (5 steps)
- Add cards flow
- Create group flow
```

**State Management:**
- Хранение состояния диалога в Redis (для scaling)
- Fallback: in-memory dict (для dev/small deployments)

---

#### 1.3. REST API (для Mini App)

**Функции:**
- CRUD операции для всех ресурсов
- Аутентификация через Telegram initData
- Пагинация и фильтрация
- WebSocket (опционально, для real-time уведомлений)

**Структура:**
```
/api/
  /auth
    POST /validate       - Validate Telegram initData
  /users
    GET  /me             - Get current user
    PATCH /me            - Update user
  /profiles
    GET  /               - List profiles
    POST /               - Create profile
    GET  /{id}           - Get profile
    PATCH /{id}          - Update profile
    DELETE /{id}         - Delete profile (soft)
    POST /{id}/activate  - Set as active
  /decks
    GET  /               - List decks
    POST /               - Create deck
    GET  /{id}           - Get deck
    PATCH /{id}          - Update deck
    DELETE /{id}         - Delete deck
    POST /{id}/activate  - Set as active
  /cards
    GET  /               - List cards (filterable by deck)
    POST /               - Create card(s)
    GET  /{id}           - Get card
    DELETE /{id}         - Delete card
    POST /rate           - Rate card (know/repeat/dont_know)
    GET  /next           - Get next card for study
  /topics
    GET  /               - List topics
    POST /               - Create topic
    GET  /{id}           - Get topic
    PATCH /{id}          - Update topic
    DELETE /{id}         - Delete topic
  /exercises
    GET  /               - Get exercise (generated)
    POST /submit         - Submit exercise answer
  /groups
    GET  /               - List groups
    POST /               - Create group
    GET  /{id}           - Get group
    PATCH /{id}          - Update group
    DELETE /{id}         - Delete group
    POST /{id}/members   - Add member (invite)
    DELETE /{id}/members/{user_id} - Remove member
    POST /{id}/materials - Add materials to group
  /stats
    GET  /               - Get user stats
    GET  /streak         - Get streak info
  /subscriptions
    GET  /status         - Get subscription status
    POST /create-checkout - Create Stripe checkout
    POST /webhook        - Stripe webhook
```

---

#### 1.4. Business Logic Layer (Services)

##### 1.4.1. User/Profile Service

**Функции:**
- CRUD для пользователей и языковых профилей
- Валидация уровней (CEFR: A1-C2)
- Управление активным профилем
- Проверка лимитов (free vs premium)

**Логика:**
```python
class UserService:
    def create_user(telegram_user) -> User
    def get_or_create_user(telegram_id) -> User
    def check_premium(user_id) -> bool
    def check_limits(user_id, action_type) -> bool

class ProfileService:
    def create_profile(user_id, language, levels, goals) -> Profile
    def validate_profile_limits(user_id) -> bool  # 1 free, unlimited premium
    def set_active_profile(user_id, profile_id)
    def delete_profile(profile_id)  # soft delete
```

---

##### 1.4.2. Flashcards Service

**Функции:**
- CRUD для колод и карточек
- SM-2 алгоритм для интервального повторения
- Генерация перевода и примеров через LLM
- Проверка дубликатов по лемме
- Выбор следующей карточки для изучения

**Логика:**
```python
class FlashcardsService:
    def create_card(word, deck_id, profile_id) -> Card
        # 1. Determine lemma (base form)
        # 2. Check duplicates
        # 3. Generate translation + example via LLM
        # 4. Save to DB

    def get_next_card(deck_id) -> Card
        # 1. Get due cards (next_review <= today)
        # 2. Sort by priority (most overdue first)
        # 3. Return top card

    def rate_card(card_id, rating: 'know'|'repeat'|'dont_know')
        # 1. Update interval based on SM-2
        # 2. Set next_review date
        # 3. Update stats

class SM2Algorithm:
    def calculate_next_interval(current_interval, rating) -> int
        if rating == 'dont_know':
            return 1  # Reset to 1 day
        elif rating == 'repeat':
            return current_interval  # No change
        else:  # 'know'
            return round(current_interval * 2.5)
```

**Приоритет карточек:**
1. Просроченные (next_review <= today) - по убыванию просрочки
2. Новые карточки (never studied)
3. Остальные не показываются

---

##### 1.4.3. Exercises Service

**Функции:**
- CRUD для тем
- Генерация упражнений через LLM (на лету, не хранятся)
- Проверка ответов через LLM
- Сохранение истории и статистики

**Логика:**
```python
class ExercisesService:
    def generate_exercise(topic_id, type: 'free_text'|'multiple_choice') -> Exercise
        # 1. Get topic info + user level
        # 2. Call LLM to generate exercise
        # 3. Return exercise (not saved to DB)

    def check_answer(exercise_data, user_answer) -> Result
        # 1. Call LLM to check answer
        # 2. Get result: correct/partial/incorrect
        # 3. Get explanation
        # 4. Save to history
        # 5. Update stats

    def suggest_topics(profile_id) -> list[Topic]
        # Call LLM with user profile to suggest 5-7 topics
```

---

##### 1.4.4. Groups Service

**Функции:**
- CRUD для групп
- Управление участниками (invite, remove)
- Шаринг материалов (decks, topics)
- Проверка лимитов (1 group free, unlimited premium)

**Логика:**
```python
class GroupsService:
    def create_group(owner_id, name, description) -> Group
    def invite_member(group_id, user_id_or_username) -> Invite
        # 1. Create invite token (expires in 7 days)
        # 2. Send notification via bot
    def accept_invite(invite_token, user_id) -> bool
    def remove_member(group_id, user_id)
    def share_material(group_id, material_type, material_id)
        # 1. Link material to group
        # 2. Notify all members
    def get_member_progress(group_id, user_id) -> Stats
```

---

##### 1.4.5. LLM/AI Service

**Функции:**
- Централизованный клиент для LLM API
- Управление промптами
- Кэширование ответов (опционально)
- Rate limiting и error handling
- Токен counting и cost tracking

**Технологии:**
- **OpenAI Python SDK** для GPT-4.1-mini
- **LangChain** (опционально, для более сложных chains)

**Логика:**
```python
class LLMService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4.1-mini"  # Может быть "gpt-4o-mini" в зависимости от версии API

    def chat(messages, system_prompt, temperature=0.7) -> str
        # Call OpenAI Chat API with retry logic

    def generate_card_content(word, language, level) -> CardContent
        # Generate translation + example + translation of example

    def generate_exercise(topic, level, type) -> Exercise

    def check_exercise_answer(question, user_answer, correct_answer) -> CheckResult

    def detect_intent(user_message, conversation_history) -> Intent
        # Определить тип запроса (translate, explain, add_card, etc.)

    def generate_response(user_message, context, profile) -> str
        # Сгенерировать ответ бота
```

**Промпты:**
Хранятся в `prompts/` директории как шаблоны (Jinja2):
```
prompts/
  system/
    teacher.txt              - Системный промпт для бота-учителя
  cards/
    generate_translation.txt
    generate_example.txt
  exercises/
    generate_free_text.txt
    generate_multiple_choice.txt
    check_answer.txt
  ...
```

---

##### 1.4.6. Stats Service

**Функции:**
- Агрегация статистики по пользователю
- Расчет стриков
- Отслеживание прогресса
- Генерация графиков (данные для frontend)

**Логика:**
```python
class StatsService:
    def get_user_stats(user_id, profile_id, period='month') -> Stats
    def calculate_streak(user_id, profile_id) -> Streak
        # 1. Get activity dates
        # 2. Find consecutive days
        # 3. Return current + best streak
    def track_activity(user_id, profile_id, action_type)
        # Save to activity log for streak calculation
    def get_cards_progress(user_id, profile_id) -> Progress
    def get_exercises_progress(user_id, profile_id) -> Progress
```

---

##### 1.4.7. Subscription Service

**Функции:**
- Интеграция с Stripe
- Управление подписками
- Проверка статуса премиум
- Обработка webhooks от Stripe

**Логика:**
```python
class SubscriptionService:
    def __init__(self):
        self.stripe = stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_checkout_session(user_id, plan: 'monthly'|'yearly') -> CheckoutSession
        # Create Stripe Checkout Session

    def handle_webhook(event) -> bool
        # Handle events: payment_succeeded, subscription_updated, etc.

    def check_premium_status(user_id) -> bool

    def cancel_subscription(user_id)

    def activate_trial(user_id, days=7)
```

---

##### 1.4.8. Media Service

**Функции:**
- Обработка изображений (OCR) - на лету, без сохранения
- Обработка голосовых сообщений (STT) - на лету, без сохранения
- Извлечение и анализ текста из медиа

**Технологии:**
- **Tesseract OCR** (pytesseract)
- **OpenAI Whisper API** для STT

**Логика:**
```python
class MediaService:
    def extract_text_from_image(image_file, language) -> str
        # 1. Download image from Telegram temporarily
        # 2. Preprocess image (resize, enhance)
        # 3. Run Tesseract OCR
        # 4. Optionally: improve with GPT-4 Vision
        # 5. Delete temporary file
        # 6. Return recognized text

    def transcribe_audio(audio_file) -> str
        # 1. Download audio from Telegram temporarily
        # 2. Convert to format supported by Whisper
        # 3. Call Whisper API
        # 4. Delete temporary file
        # 5. Return transcribed text

    def suggest_words_from_text(text, language, user_level) -> list[str]
        # Analyze text and suggest top 10 words to add
```

**Важно:** Медиа файлы обрабатываются немедленно при получении и не сохраняются в системе. Используются только временные файлы, которые удаляются после обработки.

---

##### 1.4.9. Auth Service

**Функции:**
- Аутентификация через Telegram
- Валидация Telegram initData (для Mini App) - **КРИТИЧНО для защиты от подмены user_id**
- Генерация токенов (если нужны JWT)
- Rate limiting

**Валидация Telegram initData (защита от подмены):**

Telegram Mini App передает `initData` - строку с параметрами и HMAC подписью. Это единственный способ безопасно получить user_id, которому можно доверять.

```python
import hmac
import hashlib
from urllib.parse import parse_qsl

class AuthService:
    def validate_telegram_initdata(init_data: str, bot_token: str) -> dict:
        """
        Валидирует initData от Telegram Mini App.
        Возвращает данные пользователя или выбрасывает AuthError.

        initData format: "query_id=xxx&user=%7B%22id%22%3A123...%7D&auth_date=1234567890&hash=abc123..."
        """
        # 1. Parse query string
        params = dict(parse_qsl(init_data))

        # 2. Extract hash (signature from Telegram)
        received_hash = params.pop('hash', None)
        if not received_hash:
            raise AuthError("Missing hash in initData")

        # 3. Check auth_date (timestamp) - must be < 1 hour old
        auth_date = int(params.get('auth_date', 0))
        current_time = time.time()
        if current_time - auth_date > 3600:  # 1 hour
            raise AuthError("initData expired")

        # 4. Create data-check-string (alphabetically sorted params)
        data_check_string = '\n'.join(
            f"{key}={value}"
            for key, value in sorted(params.items())
        )

        # 5. Calculate expected hash
        # HMAC-SHA256(data_check_string, secret_key)
        # where secret_key = HMAC-SHA256(bot_token, "WebAppData")
        secret_key = hmac.new(
            key="WebAppData".encode(),
            msg=bot_token.encode(),
            digestmod=hashlib.sha256
        ).digest()

        expected_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        # 6. Compare hashes (constant-time comparison)
        if not hmac.compare_digest(expected_hash, received_hash):
            raise AuthError("Invalid hash - possible tampering detected")

        # 7. Extract user data (now we can trust it!)
        user_data = json.loads(params['user'])
        # user_data contains: {"id": 123456789, "first_name": "John", ...}

        # 8. Get or create user in DB
        user = self.get_or_create_user(
            telegram_id=user_data['id'],
            first_name=user_data.get('first_name'),
            username=user_data.get('username'),
            ...
        )

        return user

    def authenticate_bot_request(telegram_update) -> User
        # Get or create user from telegram_update.message.from_user
        # Telegram Bot API already validates this for us

    def check_rate_limit(user_id, action) -> bool
        # Check daily limits for free/premium users
```

**Почему это безопасно:**

1. **HMAC подпись** - только Telegram знает bot_token, поэтому только Telegram может создать валидную подпись
2. **Невозможно подменить user_id** - если клиент попытается изменить `user` в initData, hash не совпадет
3. **Timestamp validation** - защита от replay attacks
4. **Constant-time comparison** - защита от timing attacks

**ВАЖНО:**
- Клиент НЕ должен передавать `user_id` отдельным параметром
- Backend извлекает `user_id` ТОЛЬКО из валидированного `initData`
- После валидации можно выдать JWT token для последующих запросов

---

#### 1.5. Data Access Layer

**ORM:**
- **SQLAlchemy 2.0+** (async support)
- Alembic для миграций

**Структура:**
```python
models/
  user.py          - User model
  profile.py       - LanguageProfile model
  deck.py          - Deck model
  card.py          - Card model
  topic.py         - Topic model
  group.py         - Group, GroupMember, GroupMaterial models
  session.py       - StudySession, ExerciseSession models
  stats.py         - UserStats, ActivityLog models
  subscription.py  - Subscription model

repositories/
  base.py          - BaseRepository with common CRUD
  user_repo.py
  profile_repo.py
  card_repo.py
  ...
```

**Паттерн Repository:**
```python
class BaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id) -> Model
    async def list(self, filters, limit, offset) -> list[Model]
    async def create(self, data) -> Model
    async def update(self, id, data) -> Model
    async def delete(self, id) -> bool
    async def soft_delete(self, id) -> bool

class CardRepository(BaseRepository):
    async def get_next_due_card(self, deck_id) -> Card
    async def get_by_lemma(self, lemma, profile_id) -> Card
    async def update_rating(self, card_id, rating, next_interval)
```

---

### 2. Frontend (React Mini App)

См. детали в `frontend-structure.md`, `frontend-screens.md`, `frontend-navigation.md`.

**Краткая структура:**

```
React 18.2 + TypeScript 5.0 + Vite

State Management:
  - React Query (server state)
  - Zustand (client state)
  - React Context (simple cases)

Components:
  - UI Components (Button, Card, Modal, etc.)
  - Domain Components (FlashCard, Exercise, etc.)
  - Layout Components (BottomNav, Header, etc.)

Integration:
  - @twa-dev/sdk (Telegram WebApp API)
  - Axios (REST API client)
  - Framer Motion (animations)

Routes:
  / → Home
  /practice/cards → Cards
  /practice/exercises → Exercises
  /groups → Groups
  /profile → Profile
```

---

### 3. Database (PostgreSQL)

**Версия:** PostgreSQL 14+

**Схема:**
См. детали в `backend-database.md` (будет заполнен далее).

**Основные таблицы:**
```sql
users
language_profiles
decks
cards
topics
exercises_history
groups
group_members
group_materials
study_sessions
user_stats
activity_log
subscriptions
notifications
```

**Индексы:**
- На внешние ключи (user_id, profile_id, deck_id, etc.)
- На поля для поиска (lemma, next_review, created_at)
- Composite индексы для частых запросов

**Constraints:**
- Unique constraints (lemma + profile_id для cards)
- Check constraints (levels in A1-C2)
- NOT NULL для обязательных полей

---

### 4. External Services

#### 4.1. Telegram Bot API

**Использование:**
- Получение updates (webhooks или long polling)
- Отправка сообщений, media, inline keyboards
- Telegram Payments (опционально, альтернатива Stripe)

**Webhooks vs Long Polling:**
- **Production:** Webhooks (более эффективно)
- **Development:** Long Polling (проще для локальной разработки)

---

#### 4.2. OpenAI API

**Models:**
- **GPT-4.1-mini** (gpt-4o-mini) - для всех текстовых задач
- **Whisper** - Speech-to-Text
- **GPT-4 Vision** (опционально) - для улучшения OCR

**Endpoints:**
- `/v1/chat/completions` - основной endpoint
- `/v1/audio/transcriptions` - Whisper STT

**Rate Limits:**
- Учитывать лимиты API (TPM, RPM)
- Использовать exponential backoff при ошибках
- Кэшировать повторяющиеся запросы (например, примеры для одного слова)

---

#### 4.3. Stripe API

**Использование:**
- Checkout Sessions для оформления подписки
- Webhooks для обработки событий (payment_succeeded, subscription_updated, etc.)
- Customer Portal для управления подписками

**Integration:**
- Python SDK: `stripe` library
- Frontend: Stripe Checkout (redirect или embedded)

---

#### 4.4. Redis

**Использование:**
- Кэширование (hot data: active profile, user stats)
- Session storage (bot conversation states)
- Rate limiting (counters)
- Task queue (Celery/RQ, опционально)

**Структура ключей:**
```
user:{user_id}:profile:active       → profile_id
user:{user_id}:stats:today          → JSON stats
conversation:{telegram_id}:state    → conversation state
ratelimit:{user_id}:{action}:count  → counter (TTL: 24h)
```

---

#### 4.5. Monitoring & Logging

**Sentry:**
- Error tracking
- Performance monitoring
- Release tracking

**Logging:**
- Structured logging (JSON format)
- Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Rotation и retention

**Metrics (опционально):**
- Prometheus + Grafana
- Metrics: request rate, error rate, response time, LLM costs

---

## Взаимодействие компонентов

### Поток 1: Пользователь отправляет текстовое сообщение в бот

```
1. User → Telegram → Backend (Bot Handler)
   POST /telegram-webhook/{bot_token}
   {
     "message": {
       "from": {...},
       "text": "Добавь слово casa в карточки"
     }
   }

2. Bot Handler → LLM Service
   - Detect intent: "add_card"
   - Extract word: "casa"

3. Bot Handler → Flashcards Service
   flashcards_service.create_card(word="casa", profile_id=...)

4. Flashcards Service → LLM Service
   - Generate translation: "дом"
   - Generate example: "Mi casa es tu casa"
   - Generate example translation: "Мой дом - твой дом"

5. Flashcards Service → Data Access Layer → PostgreSQL
   - Save card to DB

6. Bot Handler → Telegram Bot API
   - Send confirmation message
   - Add inline button "Удалить карточку"
```

---

### Поток 2: Пользователь открывает Mini App и начинает изучать карточки

```
1. User открывает Mini App → Telegram → Frontend
   - Frontend получает initData из Telegram WebApp API

2. Frontend → Backend REST API
   POST /api/auth/validate
   {
     "init_data": "query_id=...&user=...&hash=..."
   }

   Response: { "user": {...}, "token": "..." }

3. Frontend → Backend REST API
   GET /api/cards/next?deck_id=123
   Headers: Authorization: Bearer {token}

4. Backend (REST API) → Flashcards Service
   flashcards_service.get_next_card(deck_id=123)

5. Flashcards Service → Data Access Layer → PostgreSQL
   - Query: SELECT * FROM cards WHERE deck_id=123 AND next_review <= NOW()
   - Order by overdue DESC
   - LIMIT 1

6. Backend → Frontend
   Response: {
     "id": "card_id",
     "word": "casa",
     "translation": "дом",
     "example": "Mi casa es tu casa",
     "example_translation": "Мой дом - твой дом"
   }

7. User оценивает карточку (нажимает "Знаю")

8. Frontend → Backend REST API
   POST /api/cards/rate
   {
     "card_id": "card_id",
     "rating": "know"
   }

9. Backend (REST API) → Flashcards Service
   flashcards_service.rate_card(card_id, rating="know")

10. Flashcards Service → SM2Algorithm
    new_interval = calculate_next_interval(current=1, rating="know")
    # Returns: 3 days

11. Flashcards Service → Data Access Layer → PostgreSQL
    UPDATE cards SET interval_days=3, next_review=NOW() + INTERVAL '3 days'

12. Backend → Frontend
    Response: { "success": true, "next_review": "2025-01-12" }
```

---

### Поток 3: Пользователь отправляет голосовое сообщение в бот

```
1. User → Telegram → Backend (Bot Handler)
   POST /telegram-webhook/{bot_token}
   {
     "message": {
       "from": {...},
       "voice": {
         "file_id": "...",
         "duration": 15
       }
     }
   }

2. Bot Handler → Telegram Bot API
   GET /getFile?file_id=...
   Download audio file

3. Bot Handler → Media Service
   media_service.transcribe_audio(audio_file)

4. Media Service → OpenAI Whisper API
   POST /v1/audio/transcriptions
   Response: { "text": "Como se dice casa en ruso" }

5. Bot Handler → LLM Service
   - Detect intent: "translate"
   - Extract: word="casa", target_language="russian"

6. Bot Handler → LLM Service
   - Generate translation: "дом"

7. Bot Handler → Telegram Bot API
   - Send message: "casa - дом"
   - Add button "Добавить в карточки"
```

---

### Поток 4: Создатель группы добавляет материалы и приглашает участника

```
1. Owner → Mini App Frontend → Backend REST API
   POST /api/groups/{group_id}/materials
   {
     "material_type": "deck",
     "material_id": "deck_123"
   }

2. Backend → Groups Service
   groups_service.share_material(group_id, "deck", "deck_123")

3. Groups Service → Data Access Layer → PostgreSQL
   INSERT INTO group_materials (group_id, material_type, material_id, owner_id)

4. Groups Service → Get all group members

5. Groups Service → Notification Service (через внутренний message bus или прямой вызов)
   For each member:
     notification_service.send_notification(
       user_id=member.user_id,
       type="group_material_added",
       data={...}
     )

6. Notification Service → Telegram Bot API
   For each member:
     Send message: "[Owner] добавил колоду '[deck_name]' в группу"

7. Owner → Mini App → Backend REST API
   POST /api/groups/{group_id}/members
   {
     "username": "@john_doe"
   }

8. Backend → Groups Service
   groups_service.invite_member(group_id, username="@john_doe")

9. Groups Service:
   - Find user by username in DB
   - Create invite token (UUID)
   - Save to invites table with expiry (7 days)

10. Groups Service → Notification Service → Telegram Bot API
    Send message to @john_doe:
      "[Owner] приглашает вас в группу '[Group Name]'"
      Inline buttons: [Принять] [Отклонить]

11. Member нажимает "Принять"

12. Bot Handler → Groups Service
    groups_service.accept_invite(invite_token, user_id)

13. Groups Service → Data Access Layer → PostgreSQL
    INSERT INTO group_members (group_id, user_id)
    DELETE FROM invites WHERE token=...

14. Groups Service → Notification Service → Telegram Bot API
    Send to owner: "@john_doe принял приглашение"
    Send to member: "Вы присоединились к группе"
```

---

## Data Flow

### Диаграмма потока данных для ключевых операций

```
┌─────────────────────────────────────────────────────────────────┐
│                     Data Flow: Add Card                          │
└─────────────────────────────────────────────────────────────────┘

User Input (Bot/Mini App)
    │
    ▼
┌────────────────┐
│ Validate Input │ (word exists, profile active)
└────────┬───────┘
         │
         ▼
┌────────────────┐
│ Check Duplicate│ (lemma + profile_id)
└────────┬───────┘
         │
         ├─ Duplicate found → Return error
         │
         └─ No duplicate
                │
                ▼
         ┌──────────────┐
         │   LLM Call   │ (generate translation + example)
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │  Save to DB  │
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │Return Success│
         └──────────────┘
```

```
┌─────────────────────────────────────────────────────────────────┐
│                   Data Flow: Study Session                       │
└─────────────────────────────────────────────────────────────────┘

Start Session
    │
    ▼
┌────────────────┐
│  Load Deck     │
└────────┬───────┘
         │
         ▼
┌────────────────┐
│ Get Next Card  │ (due cards sorted by priority)
└────────┬───────┘
         │
         ├─ No cards → Show "All done!"
         │
         └─ Card found
                │
                ▼
         ┌──────────────┐
         │  Show Card   │
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │ User Rates   │ (know/repeat/dont_know)
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │Calculate Next│ (SM-2 algorithm)
         │   Interval   │
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │ Update Card  │ (interval, next_review)
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │ Update Stats │
         └──────┬───────┘
                │
                ▼
         Loop → Get Next Card
```

---

## Масштабируемость

### Horizontal Scaling

#### Backend

**Stateless Design:**
- Backend сервисы должны быть stateless
- Состояние хранится в DB/Redis, не в памяти приложения
- Позволяет запускать несколько инстансов за load balancer

**Load Balancer:**
- Nginx / Traefik / AWS ALB
- Round-robin или least-connections

**Deployment:**
```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                         │
└────┬─────────────┬─────────────┬─────────────┬──────────┘
     │             │             │             │
     ▼             ▼             ▼             ▼
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│Backend 1│   │Backend 2│   │Backend 3│   │Backend N│
└────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
     │             │             │             │
     └─────────────┴─────────────┴─────────────┘
                         │
                         ▼
                 ┌──────────────┐
                 │  PostgreSQL  │
                 │   (Primary)  │
                 └──────┬───────┘
                        │ Replication
                        ▼
                 ┌──────────────┐
                 │  PostgreSQL  │
                 │  (Read Replica)│
                 └──────────────┘
```

**Database:**
- **Write:** Primary DB
- **Read:** Read replicas (для heavy read operations: stats, lists)
- Connection pooling (pgBouncer)

**Caching:**
- Redis для кэширования hot data
- Cache invalidation стратегия (TTL + manual invalidation)

**Task Queue (для async операций):**
- Celery + Redis/RabbitMQ
- Tasks:
  - Send bulk notifications
  - Generate reports
  - Process uploaded media
  - Clean up old data

---

#### Database Partitioning (если очень большой объем)

**Partitioning by user_id:**
- Разбить таблицы на партиции по hash(user_id)
- PostgreSQL native partitioning

**Sharding (крайний случай):**
- Горизонтальный sharding по user_id
- Каждый shard - отдельная DB instance
- Shard router в application layer

---

#### Caching Strategy

**Levels:**

1. **Application-level cache** (Redis)
   - User profiles (TTL: 1 hour)
   - Active deck/topic (TTL: 30 min)
   - Stats (TTL: 5 min)

2. **Database query cache**
   - PostgreSQL query cache (automatic)

3. **CDN** (для static assets в Mini App)
   - CloudFlare / AWS CloudFront

---

### Vertical Scaling

**Database:**
- Increase RAM для PostgreSQL (большой shared_buffers)
- Faster storage (NVMe SSD)

**Backend:**
- Increase CPU/RAM для instances
- Но horizontal scaling предпочтительнее

---

### Auto-scaling

**Kubernetes (K8s):**
- Horizontal Pod Autoscaler (HPA)
- Metrics: CPU, memory, request rate
- Min replicas: 2, Max replicas: 10

**Serverless (альтернатива):**
- AWS Lambda / Google Cloud Functions
- Auto-scaling из коробки
- Но есть cold start latency

---

### Performance Optimization

**Database:**
- Индексы на частых запросах
- EXPLAIN ANALYZE для оптимизации
- Materialized views для сложных агрегаций (stats)
- Connection pooling

**API:**
- Pagination (limit/offset или cursor-based)
- Field filtering (GraphQL-style или query params)
- Compression (gzip)
- HTTP/2

**LLM:**
- Batching requests где возможно
- Caching похожих промптов
- Использовать более дешевые модели где возможно

---

## Безопасность

### Authentication & Authorization

**Telegram Authentication (Mini App):**

**КРИТИЧНО:** User ID получается ТОЛЬКО через валидацию Telegram `initData`. Никогда не принимать `user_id` от клиента напрямую!

Алгоритм:
1. Frontend получает `initData` от Telegram WebApp API (`window.Telegram.WebApp.initData`)
2. Frontend отправляет `initData` на backend endpoint `/api/auth/validate`
3. Backend проверяет HMAC-SHA256 подпись:
   - `secret_key = HMAC-SHA256(bot_token, "WebAppData")`
   - `expected_hash = HMAC-SHA256(data_check_string, secret_key)`
   - Сравнивает с полученным hash (constant-time comparison)
4. Backend проверяет `auth_date` (< 1 час)
5. Если валидация прошла - извлекаем `user_id` из `initData.user.id`
6. Backend возвращает JWT token с `user_id` в payload
7. Все последующие запросы используют этот JWT token

**Защита от атак:**
- ❌ Клиент не может подменить `user_id` - подпись станет невалидной
- ❌ Replay attacks - защита через `auth_date` timestamp
- ❌ Man-in-the-middle - все запросы через HTTPS/TLS 1.3

**Telegram Bot Authentication:**
- Telegram Bot API автоматически валидирует запросы
- `telegram_update.message.from_user.id` уже проверен Telegram

**JWT Tokens:**
- После валидации `initData` выдается JWT access token
- Payload: `{"user_id": 123456789, "exp": ..., "iat": ...}`
- Подписан secret key сервера
- **Access Token TTL:** 30 минут (короткий срок для безопасности)
- **Refresh Token (опционально):** 7 дней, хранится в DB для возможности revoke
- При истечении access token клиент перевалидирует через `initData` или использует refresh token

**Authorization:**
- Role-based: user, premium_user, admin
- Resource ownership checks (user can only access their data)
- Group permissions (owner, member)
- Каждый endpoint проверяет: `if resource.owner_id != request.user.id: raise Forbidden`

---

### Rate Limiting

**Per-user limits:**
- Free: 50 messages/day, 10 exercises/day
- Premium: 500 messages/day, unlimited exercises
- Admin: unlimited

**Implementation:**
- Redis counters with TTL (24 hours)
- Key: `ratelimit:{user_id}:{action}`
- Sliding window или fixed window

**Global limits:**
- API rate limit: 100 req/min per IP (защита от DDoS)
- Fail2ban для блокировки malicious IPs

---

### Data Security

**Encryption:**
- HTTPS for all communications (TLS 1.3)
- Database encryption at rest (PostgreSQL native или disk-level)
- Encrypted backups

**Sensitive Data:**
- Hash passwords если есть (но в нашем случае auth через Telegram)
- PII (Personally Identifiable Information) - минимизировать хранение
- GDPR compliance: право на удаление данных

**API Keys:**
- Environment variables (never in code)
- Secrets management (AWS Secrets Manager / HashiCorp Vault)
- Rotate keys periodically

---

### Input Validation

**Backend:**
- Pydantic models для валидации
- Sanitize user input (защита от injection)
- Max lengths для strings
- Whitelist allowed characters

**LLM:**
- OpenAI Moderation API для фильтрации неприемлемого контента
- Rate limiting на LLM calls
- Cost monitoring

---

### OWASP Top 10

**Protection against:**

1. **Injection (SQL, NoSQL):**
   - Use ORM (SQLAlchemy) with parameterized queries

2. **Broken Authentication:**
   - Validate Telegram initData properly
   - Session management в Redis

3. **Sensitive Data Exposure:**
   - HTTPS, encryption at rest

4. **XML External Entities (XXE):**
   - N/A (не используем XML)

5. **Broken Access Control:**
   - Authorization checks на каждом endpoint
   - User can only access their resources

6. **Security Misconfiguration:**
   - Security headers (CSP, HSTS, X-Frame-Options)
   - Hide error details in production

7. **Cross-Site Scripting (XSS):**
   - Sanitize output в Mini App (React защищает автоматически)

8. **Insecure Deserialization:**
   - Validate JSON input structure

9. **Using Components with Known Vulnerabilities:**
   - Dependabot / Snyk для мониторинга dependencies
   - Regular updates

10. **Insufficient Logging & Monitoring:**
    - Structured logging
    - Sentry для errors
    - Audit logs для admin actions

---

### DDoS Protection

**CloudFlare:**
- CDN + DDoS protection
- WAF (Web Application Firewall)
- Rate limiting на edge

**Backend:**
- Connection limits
- Request timeouts
- Resource quotas per user

---

### Backup & Disaster Recovery

**Database Backups:**
- Automated daily backups
- Point-in-time recovery (PostgreSQL WAL)
- Store backups in different region
- Test recovery процедуры quarterly

**Code:**
- Version control (Git)
- Tagged releases
- Rollback strategy

**RTO/RPO:**
- Recovery Time Objective: < 1 hour
- Recovery Point Objective: < 15 minutes (WAL-based recovery)

---

## Deployment Architecture

### Production Environment

```
┌──────────────────────────────────────────────────────────────┐
│                        CloudFlare                             │
│                    (CDN + DDoS Protection)                    │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                   Ingress Controller                    │  │
│  │                  (nginx-ingress)                        │  │
│  └────────────────────┬────────────────────────────────────┘  │
│                       │                                       │
│  ┌────────────────────┴────────────────────────────────┐     │
│  │                                                      │     │
│  │  ┌────────────────┐          ┌────────────────┐     │     │
│  │  │  Backend Pods  │          │ Frontend Pods  │     │     │
│  │  │  (FastAPI)     │          │ (Nginx+React)  │     │     │
│  │  │  Replicas: 3   │          │  Replicas: 2   │     │     │
│  │  └────────┬───────┘          └────────────────┘     │     │
│  │           │                                          │     │
│  │  ┌────────▼───────┐          ┌────────────────┐     │     │
│  │  │  Redis Pods    │          │  Celery Workers│     │     │
│  │  │  Replicas: 2   │          │  Replicas: 2   │     │     │
│  │  └────────────────┘          └────────────────┘     │     │
│  └─────────────────────────────────────────────────────┘     │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                   Managed Database                            │
│              (AWS RDS / GCP Cloud SQL)                        │
│                   PostgreSQL 14                               │
│                                                               │
│  Primary (write) + Read Replica (read)                        │
└──────────────────────────────────────────────────────────────┘
```

**Infrastructure:**
- **Kubernetes** (AWS EKS / GCP GKE / DigitalOcean Kubernetes)
- **Helm** для deployments
- **ArgoCD** для GitOps

---

### Environments

1. **Development:**
   - Local docker-compose
   - SQLite или local PostgreSQL
   - Mock external services (LLM, Stripe)

2. **Staging:**
   - Kubernetes namespace
   - Shared DB instance
   - Real external services (test keys)

3. **Production:**
   - Dedicated cluster/namespace
   - Managed DB with backups
   - Real external services

---

### CI/CD Pipeline

См. детали в `ci-cd.md` (будет заполнен).

**Краткий flow:**
```
Git Push
  ↓
GitHub Actions
  ↓
1. Run tests
2. Build Docker images
3. Push to registry
4. Deploy to staging (auto)
5. Run E2E tests
6. Deploy to production (manual approval)
  ↓
Kubernetes
```

---

### Monitoring & Alerting

**Metrics:**
- Application: response time, error rate, throughput
- Infrastructure: CPU, memory, disk, network
- Business: cards created, exercises completed, active users

**Tools:**
- **Prometheus** (metrics collection)
- **Grafana** (dashboards)
- **AlertManager** (alerts)
- **Sentry** (error tracking)

**Alerts:**
- Error rate > 1%
- Response time > 1s (p95)
- Database connections > 80%
- Disk usage > 85%
- Cost spike (LLM API calls)

---

## Technology Stack Summary

### Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.0 (async)
- **DB:** PostgreSQL 14+
- **Cache:** Redis 7+
- **Task Queue:** Celery (optional)
- **Telegram:** python-telegram-bot 20+
- **LLM:** OpenAI Python SDK
- **Testing:** pytest, pytest-asyncio
- **Linting:** ruff, mypy

### Frontend
- **Language:** TypeScript 5.0+
- **Framework:** React 18.2+
- **Build:** Vite 4+
- **State:** React Query + Zustand
- **UI:** Custom + Radix UI + Framer Motion
- **Telegram:** @twa-dev/sdk
- **Testing:** Vitest + React Testing Library

### Infrastructure
- **Container:** Docker
- **Orchestration:** Kubernetes
- **CI/CD:** GitHub Actions
- **Monitoring:** Prometheus + Grafana + Sentry
- **Cloud:** AWS / GCP / DigitalOcean

### External
- **LLM:** OpenAI (GPT-4.1-mini, Whisper)
- **Payments:** Stripe
- **OCR:** Tesseract
- **CDN:** CloudFlare

---

Этот документ описывает полную архитектуру Telegram-бота для изучения языков с ИИ-преподавателем, включая компоненты системы, взаимодействие, масштабируемость и безопасность.
