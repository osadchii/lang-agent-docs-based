# Backend API Specification

## Общие принципы

### Архитектура
- **Стиль:** REST API
- **Формат:** JSON для всех запросов и ответов
- **Протокол:** HTTPS (TLS 1.3)
- **Base URL:** `https://api.example.com/api`

### Аутентификация

**Для Mini App (КРИТИЧНО!):**

Mini App использует Telegram WebApp `initData` для аутентификации. Это единственный безопасный способ получить валидный `user_id`.

**Алгоритм валидации initData:**

1. Frontend получает `initData` от Telegram WebApp API: `window.Telegram.WebApp.initData`
2. Frontend отправляет `initData` на endpoint `/api/auth/validate`
3. Backend проверяет HMAC-SHA256 подпись:
   ```python
   secret_key = HMAC-SHA256(bot_token, "WebAppData")
   expected_hash = HMAC-SHA256(data_check_string, secret_key)
   ```
4. Backend проверяет `auth_date` (должен быть < 1 час)
5. Если валидация успешна - извлекается `user_id` из `initData.user.id`
6. Backend возвращает JWT token с `user_id` в payload
7. Все последующие запросы используют этот JWT token

**Для Telegram Bot:**
- Bot API автоматически валидирует запросы от Telegram
- `telegram_update.message.from_user.id` уже проверен Telegram

**JWT Token:**
```json
{
  "user_id": 123456789,
  "telegram_id": 123456789,
  "is_premium": true,
  "iat": 1234567890,
  "exp": 1234653890
}
```

- **TTL:** 30 минут
- **Algorithm:** HS256
- **Header:** `Authorization: Bearer <token>`
- **Note:** При истечении токена клиент запрашивает новый через `/api/auth/validate` с актуальным `initData`

### CORS
- Разрешённые origin:
  - `https://webapp.telegram.org` (Telegram Mini App)
  - `PRODUCTION_APP_ORIGIN` из конфигурации (боевой фронтенд)
  - локальные клиенты `http://localhost:<port>` из `BACKEND_CORS_ORIGINS` (строго localhost, учитываются только при `APP_ENV=local/test`)
- Пример заголовков:
  ```
  Access-Control-Allow-Origin: https://webapp.telegram.org
  Access-Control-Allow-Methods: GET, POST, PATCH, DELETE, OPTIONS
  Access-Control-Allow-Headers: Content-Type, Authorization
  Access-Control-Max-Age: 86400
  ```

### Ограничение размера запросов
- Любой HTTP-запрос с телом больше `MAX_REQUEST_BYTES` (по умолчанию 32 MiB) получает `413 Request Entity Too Large`.
- Значение можно понизить/повысить через переменную окружения `MAX_REQUEST_BYTES`. Порог увеличен ради загрузки до трёх изображений по 10 МБ для OCR, но рекомендуется не опускаться ниже профиля пользователя.
- Ответ везде следует контракту ошибок:
  ```json
  {
    "error": {
      "code": "PAYLOAD_TOO_LARGE",
      "message": "Request body exceeds MAX_REQUEST_BYTES limit."
    }
  }
  ```

### Rate Limiting

**Per-user limits:**
- Free users:
  - 50 LLM messages/day
  - 10 exercises/day
  - 200 cards max
- Premium users:
  - 500 LLM messages/day
  - Unlimited exercises
  - Unlimited cards

**Global limits:**
- 100 requests/minute per IP (защита от DDoS)
- 1000 requests/hour per user

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

**При превышении:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Превышен лимит запросов. Попробуйте через 42 секунды.",
    "retry_after": 42
  }
}
```

## Медиа / OCR

### `POST /api/media/ocr`
- **Назначение:** распознать текст на изображении и предложить слова для карточек (см. UC‑5 в `docs/use-cases.md`).
- **Авторизация:** требуется.
- **Тело:** `multipart/form-data`
  - `images`: 1–3 файлов `image/jpeg|png|webp|heic`, каждый ≤ `OCR_MAX_IMAGE_BYTES` (по умолчанию 10 МБ).
  - `profile_id` (опционально): UUID; если не указан, используется активный профиль пользователя.
- **Ответ:**

```json
{
  "profile_id": "2b5588c1-....",
  "target_language": "es",
  "target_language_name": "Spanish",
  "combined_text": "Hola, este es un ejemplo…",
  "has_target_language": true,
  "detected_languages": ["es"],
  "segments": [
    {
      "image_index": 0,
      "detected_languages": ["es"],
      "contains_target_language": true,
      "confidence": "high",
      "full_text": "Hola, este es un ejemplo",
      "target_text": "Hola, este es un ejemplo"
    }
  ],
  "suggestions": [
    {
      "word": "viajar",
      "type": "verb",
      "reason": "Полезный глагол для путешествий",
      "priority": 1
    }
  ]
}
```

- **Ошибки:**
  - `400 INVALID_FIELD_VALUE` — приложено слишком много изображений или превышен размер.
  - `404 PROFILE_NOT_FOUND` — профиль не найден/неактивен.
  - `502 LLM_SERVICE_ERROR` — GPT‑4 Vision недоступен.

### Пагинация

**Query parameters:**
```
GET /api/cards?limit=20&offset=0
```

- `limit` - количество элементов (по умолчанию: 20, макс: 100)
- `offset` - сдвиг (по умолчанию: 0)

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

### Фильтрация и сортировка

**Query parameters:**
```
GET /api/cards?deck_id=123&status=new&sort=-created_at
```

- Префикс `-` для сортировки по убыванию
- Несколько фильтров через `&`

---

## Endpoints

### POST /telegram-webhook/{bot_token}

Webhook для Telegram Bot API. Endpoint принимает JSON-обновления напрямую от Telegram и делегирует их python-telegram-bot приложению.

- **URL:** `/telegram-webhook/<bot_token>`
- **Headers:** стандартные Telegram (`Content-Type: application/json`)
- **Body:** нативный Update объект из Bot API (messages, callback_query, etc.)

**Response 200 OK:**
```json
{
  "ok": true
}
```

**Ошибки:**
- `403 FORBIDDEN` (`error.code = "FORBIDDEN"`) — если path token не совпадает с `TELEGRAM_BOT_TOKEN`
- `4xx/5xx` по контракту ошибок (см. ниже) при некорректном JSON или внутренних сбоях

> Примечание: В production окружениях webhook URL формируется автоматически как `https://<BACKEND_DOMAIN>/telegram-webhook/<bot_token>`. Backend проверяет, что домен резолвится, и в противном случае пропускает настройку; для локальной разработки бот запускается командой `python -m app.telegram.polling` (см. `docs/backend-telegram.md`).

### Health Check

#### GET /health

Health check endpoint для мониторинга состояния сервиса и его зависимостей.

**Использование:**
- CI/CD проверка после деплоя
- Мониторинг и алертинг
- Load balancer health checks
- Docker healthcheck

**Response 200 OK:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-09T12:00:00Z",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "openai": "ok",
    "stripe": "ok"
  },
  "version": "1.0.0"
}
```

**Response 503 Service Unavailable:**
```json
{
  "status": "unhealthy",
  "timestamp": "2025-01-09T12:00:00Z",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "openai": "error",
    "stripe": "ok"
  },
  "errors": [
    {
      "service": "openai",
      "message": "Connection timeout after 5s"
    }
  ],
  "version": "1.0.0"
}
```

**Проверки:**
- **database** - PostgreSQL connectivity (SELECT 1)
- **redis** - Redis connectivity (PING)
- **openai** - OpenAI API availability (не обязательно блокирует 200, но отмечается в checks)
- **stripe** - Stripe API availability (не обязательно блокирует 200, но отмечается в checks)

**Статусы:**
- `200 OK` - сервис полностью работоспособен, все критичные зависимости доступны (database, redis)
- `503 Service Unavailable` - критичная зависимость недоступна

**Примечание:**
- Endpoint не требует аутентификации
- Timeout: 5 секунд
- Недоступность внешних API (OpenAI, Stripe) не переводит сервис в статус 503, но отмечается в `checks`

---

### 1. Authentication

#### POST /api/auth/validate

Валидация Telegram initData и выдача JWT token.

**Request:**
```json
{
  "init_data": "query_id=xxx&user=%7B%22id%22%3A123...%7D&auth_date=1234567890&hash=abc123..."
}
```

**Response 200:**
```json
{
  "user": {
    "id": "uuid",
    "telegram_id": 123456789,
    "first_name": "John",
    "last_name": "Doe",
    "username": "johndoe",
    "is_premium": false,
    "trial_ends_at": "2025-01-15T00:00:00Z",
    "created_at": "2025-01-08T12:00:00Z"
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-01-09T12:00:00Z"
}
```

**Errors:**
- `400 INVALID_INIT_DATA` - Invalid or expired initData
- `401 AUTH_FAILED` - Hash verification failed

---

### 2. Диалоги (Mini App chat)

#### POST /api/sessions/chat

Минимальная точка входа для Mini App: принимает текст пользователя, использует `DialogService` и возвращает сохранённое сообщение ассистента.

**Request:**
```json
{
  "message": "Как сказать «где метро» по-испански?",
  "profile_id": "63adf64b-0000-48a1-92d9-bd516c1eae9d"
}
```

- `message` — обязательный текст (1–2000 символов)
- `profile_id` — опционально, если не передан берётся активный или создаётся дефолтный профиль

**Response 201:**
```json
{
  "profile_id": "63adf64b-0000-48a1-92d9-bd516c1eae9d",
  "message": {
    "id": "f6ad0d4f-4c1f-47cb-9f73-dc4ba1230b92",
    "profile_id": "63adf64b-0000-48a1-92d9-bd516c1eae9d",
    "role": "assistant",
    "content": "Можно сказать «¿Dónde está el metro?» и уточнить станцию...",
    "timestamp": "2025-01-10T12:01:02.345678+00:00"
  }
}
```

**Errors:**
- `401 AUTH_FAILED` — отсутствует или просрочен JWT
- `404 PROFILE_NOT_FOUND` — профиль не принадлежит пользователю
- `422 VALIDATION_ERROR` — пустое сообщение / превышены лимиты
- `502 LLM_SERVICE_ERROR` — внешнее LLM временно недоступно

---

#### GET /api/dialog/history

Отдаёт историю переписки для Mini App. Сообщения внутри страницы отсортированы от старых к новым.

**Query параметры:**
- `profile_id` — опционально
- `limit` — 1..50 (по умолчанию 20)
- `offset` — 0..200 (по умолчанию 0)

**Response 200:**
```json
{
  "messages": [
    {
      "id": "3fb7dc2b-9be8-4b27-8e6c-cdb45ed17d9c",
      "profile_id": "63adf64b-0000-48a1-92d9-bd516c1eae9d",
      "role": "user",
      "content": "Как вежливо обратиться к тренеру в Италии?",
      "timestamp": "2025-01-10T11:59:00.000000+00:00"
    },
    {
      "id": "c67d2c0e-73a9-4f44-9d2f-8da7f5cb2e4e",
      "profile_id": "63adf64b-0000-48a1-92d9-bd516c1eae9d",
      "role": "assistant",
      "content": "Используйте «Buongiorno, professore/professoressa» и добавьте имя.",
      "timestamp": "2025-01-10T11:59:02.120000+00:00"
    }
  ],
  "pagination": {
    "limit": 2,
    "offset": 0,
    "count": 2,
    "has_more": true,
    "next_offset": 2
  }
}
```

**Errors:**
- `401 AUTH_FAILED` — требуется авторизация
- `400 INVALID_FIELD_VALUE` — превышено ограничение `limit + offset > 200`
- `404 PROFILE_NOT_FOUND` — профиль не найден

---

### 3. Users

#### GET /api/users/me

Получить информацию о текущем пользователе.

**Response 200:**
```json
{
  "id": "uuid",
  "telegram_id": 123456789,
  "first_name": "John",
  "last_name": "Doe",
  "username": "johndoe",
  "is_premium": false,
  "subscription": {
    "status": "trial",
    "plan": null,
    "expires_at": "2025-01-15T00:00:00Z"
  },
  "limits": {
    "profiles": { "used": 1, "max": 1 },
    "messages": { "used": 15, "max": 50, "reset_at": "2025-01-09T00:00:00Z" },
    "exercises": { "used": 3, "max": 10, "reset_at": "2025-01-09T00:00:00Z" },
    "cards": { "used": 45, "max": 200 },
    "groups": { "used": 0, "max": 1 }
  },
  "created_at": "2025-01-08T12:00:00Z"
}
```

#### PATCH /api/users/me

Обновить информацию пользователя (ограниченный набор полей).

**Request:**
```json
{
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response 200:**
```json
{
  "id": "uuid",
  "telegram_id": 123456789,
  "first_name": "John",
  "last_name": "Doe",
  "username": "johndoe",
  ...
}
```

---

### 4. Language Profiles

#### GET /api/profiles

Список языковых профилей пользователя.

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "language": "es",
      "language_name": "Испанский",
      "current_level": "A2",
      "target_level": "B1",
      "goals": ["work", "travel"],
      "interface_language": "ru",
      "is_active": true,
      "progress": {
        "cards_count": 124,
        "exercises_count": 48,
        "streak": 12
      },
      "created_at": "2025-01-01T12:00:00Z",
      "updated_at": "2025-01-08T12:00:00Z"
    }
  ]
}
```

#### POST /api/profiles

Создать новый языковой профиль.

**Request:**
```json
{
  "language": "es",
  "current_level": "A2",
  "target_level": "B1",
  "goals": ["work", "travel"],
  "interface_language": "ru"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "language": "es",
  "language_name": "Испанский",
  "current_level": "A2",
  "target_level": "B1",
  "goals": ["work", "travel"],
  "interface_language": "ru",
  "is_active": false,
  "created_at": "2025-01-08T12:00:00Z"
}
```

**Errors:**
- `400 LIMIT_REACHED` - Достигнут лимит профилей (1 для free)
- `400 DUPLICATE_LANGUAGE` - Профиль для этого языка уже существует
- `400 INVALID_LEVEL` - Неверный CEFR уровень
- `400 TARGET_BELOW_CURRENT` - Целевой уровень ниже текущего

#### GET /api/profiles/{profile_id}

Получить конкретный профиль.

**Response 200:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "language": "es",
  ...
}
```

**Errors:**
- `404 PROFILE_NOT_FOUND`

#### PATCH /api/profiles/{profile_id}

Обновить профиль.

**Request:**
```json
{
  "current_level": "B1",
  "target_level": "B2",
  "goals": ["work", "study"],
  "interface_language": "es"
}
```

**Response 200:**
```json
{
  "id": "uuid",
  ...
}
```

**Note:** Поле `language` изменить нельзя.

#### DELETE /api/profiles/{profile_id}

Удалить профиль (soft delete).

**Response 204 No Content**

**Errors:**
- `400 LAST_PROFILE` - Нельзя удалить последний профиль
- `404 PROFILE_NOT_FOUND`

#### POST /api/profiles/{profile_id}/activate

Установить профиль как активный.

**Response 200:**
```json
{
  "id": "uuid",
  "is_active": true,
  ...
}
```

---

### 5. Decks

#### GET /api/decks

Список колод для активного профиля.

**Query params:**
- `profile_id` (optional) - если не указан, используется активный профиль
- `include_group` (optional, default: true) - включать групповые колоды

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "profile_id": "uuid",
      "name": "Мои слова",
      "description": null,
      "is_active": true,
      "is_group": false,
      "owner_id": null,
      "owner_name": null,
      "cards_count": 45,
      "new_cards_count": 12,
      "due_cards_count": 8,
      "created_at": "2025-01-01T12:00:00Z",
      "updated_at": "2025-01-08T12:00:00Z"
    },
    {
      "id": "uuid",
      "profile_id": "uuid",
      "name": "Времена испанского",
      "is_active": false,
      "is_group": true,
      "owner_id": "uuid",
      "owner_name": "Maria",
      "cards_count": 120,
      "new_cards_count": 45,
      "due_cards_count": 0,
      ...
    }
  ]
}
```

#### POST /api/decks

Создать новую колоду.

**Request:**
```json
{
  "name": "Еда и напитки",
  "description": "Лексика по теме еда",
  "profile_id": "uuid"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "profile_id": "uuid",
  "name": "Еда и напитки",
  "description": "Лексика по теме еда",
  "is_active": false,
  "is_group": false,
  "cards_count": 0,
  "created_at": "2025-01-08T12:00:00Z"
}
```

#### GET /api/decks/{deck_id}

Получить детали колоды.

**Response 200:**
```json
{
  "id": "uuid",
  "name": "Мои слова",
  "description": null,
  "is_active": true,
  "is_group": false,
  "cards_count": 45,
  "new_cards_count": 12,
  "due_cards_count": 8,
  "stats": {
    "know": 20,
    "repeat": 10,
    "dont_know": 3,
    "new": 12
  },
  "created_at": "2025-01-01T12:00:00Z"
}
```

#### PATCH /api/decks/{deck_id}

Обновить колоду.

**Request:**
```json
{
  "name": "Мои слова (обновлено)",
  "description": "Основные слова для начинающих"
}
```

**Response 200:**
```json
{
  "id": "uuid",
  "name": "Мои слова (обновлено)",
  ...
}
```

**Errors:**
- `403 FORBIDDEN` - Нельзя редактировать групповую колоду

#### DELETE /api/decks/{deck_id}

Удалить колоду (soft delete).

**Response 204 No Content**

**Errors:**
- `400 LAST_DECK` - Нельзя удалить единственную колоду
- `403 FORBIDDEN` - Нельзя удалить групповую колоду

#### POST /api/decks/{deck_id}/activate

Установить колоду как активную.

**Response 200:**
```json
{
  "id": "uuid",
  "is_active": true,
  ...
}
```

---

### 6. Cards

#### GET /api/cards

Список карточек.

**Query params:**
- `deck_id` (required) - ID колоды
- `status` (optional) - фильтр по статусу: `new`, `learning`, `review`
- `search` (optional) - поиск по слову или переводу
- `limit`, `offset` - пагинация

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "deck_id": "uuid",
      "word": "casa",
      "translation": "дом",
      "example": "Mi casa es tu casa",
      "example_translation": "Мой дом - твой дом",
      "lemma": "casa",
      "status": "learning",
      "interval_days": 3,
      "next_review": "2025-01-11T12:00:00Z",
      "reviews_count": 5,
      "last_rating": "know",
      "created_at": "2025-01-05T12:00:00Z"
    }
  ],
  "pagination": {
    "total": 45,
    "limit": 20,
    "offset": 0
  }
}
```

#### POST /api/cards

Создать карточку (одну или несколько).

**Request (одна карточка):**
```json
{
  "deck_id": "uuid",
  "words": ["verano"]
}
```

**Request (список):**
```json
{
  "deck_id": "uuid",
  "words": ["verano", "invierno", "primavera", "otoño"]
}
```

**Response 201:**
```json
{
  "created": [
    {
      "id": "uuid",
      "deck_id": "uuid",
      "word": "verano",
      "translation": "лето",
      "example": "En verano hace mucho calor",
      "example_translation": "Летом очень жарко",
      "lemma": "verano",
      "status": "new",
      "created_at": "2025-01-08T12:00:00Z"
    }
  ],
  "duplicates": [],
  "failed": []
}
```

**Errors:**
- `400 LIMIT_REACHED` - Достигнут лимит карточек (200 для free)
- `400 DUPLICATE_LEMMA` - Карточка с такой леммой уже существует
- `400 TOO_MANY_WORDS` - Максимум 20 слов за раз
- `402 PAYMENT_REQUIRED` - Требуется премиум

#### GET /api/cards/{card_id}

Получить карточку.

**Response 200:**
```json
{
  "id": "uuid",
  "deck_id": "uuid",
  "word": "casa",
  "translation": "дом",
  "example": "Mi casa es tu casa",
  "example_translation": "Мой дом - твой дом",
  "lemma": "casa",
  "status": "learning",
  "interval_days": 3,
  "next_review": "2025-01-11T12:00:00Z",
  "reviews_count": 5,
  "history": [
    {
      "date": "2025-01-08T12:00:00Z",
      "rating": "know",
      "interval_before": 1,
      "interval_after": 3
    }
  ],
  "created_at": "2025-01-05T12:00:00Z"
}
```

#### DELETE /api/cards/{card_id}

Удалить карточку.

**Response 204 No Content**

**Errors:**
- `403 FORBIDDEN` - Нельзя удалить групповую карточку

#### POST /api/cards/{card_id}/regenerate-example

Регенерировать пример использования через LLM.

**Response 200:**
```json
{
  "id": "uuid",
  "example": "Vivo en una casa grande",
  "example_translation": "Я живу в большом доме"
}
```

#### GET /api/cards/next

Получить следующую карточку для изучения.

**Query params:**
- `deck_id` (optional) - если не указан, используется активная колода

**Response 200:**
```json
{
  "id": "uuid",
  "deck_id": "uuid",
  "word": "casa",
  "translation": "дом",
  "example": "Mi casa es tu casa",
  "example_translation": "Мой дом - твой дом",
  "side": "learning",
  "status": "review",
  "next_review": "2025-01-08T12:00:00Z"
}
```

**Response 204 No Content** - нет карточек для изучения

#### POST /api/cards/rate

Оценить карточку.

**Request:**
```json
{
  "card_id": "uuid",
  "rating": "know"
}
```

**Values:** `"know"`, `"repeat"`, `"dont_know"`

**Response 200:**
```json
{
  "id": "uuid",
  "interval_days": 8,
  "next_review": "2025-01-16T12:00:00Z",
  "status": "review"
}
```

---

### 7. Topics

#### GET /api/topics

Список тем для активного профиля.

**Query params:**
- `profile_id` (optional)
- `type` (optional) - `grammar`, `vocabulary`, `situation`
- `include_group` (optional, default: true)

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "profile_id": "uuid",
      "name": "Pretérito Perfecto",
      "description": "Прошедшее время (я сделал, ты сделал...)",
      "type": "grammar",
      "is_active": true,
      "is_group": false,
      "owner_id": null,
      "owner_name": null,
      "exercises_count": 24,
      "accuracy": 0.85,
      "created_at": "2025-01-01T12:00:00Z"
    }
  ]
}
```

#### POST /api/topics

Создать новую тему.

**Request:**
```json
{
  "name": "Ser vs Estar",
  "description": "Различия между ser и estar",
  "type": "grammar",
  "profile_id": "uuid"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "name": "Ser vs Estar",
  "description": "Различия между ser и estar",
  "type": "grammar",
  "is_active": false,
  "created_at": "2025-01-08T12:00:00Z"
}
```

#### GET /api/topics/{topic_id}

Получить детали темы.

**Response 200:**
```json
{
  "id": "uuid",
  "name": "Pretérito Perfecto",
  "description": "Прошедшее время",
  "type": "grammar",
  "is_active": true,
  "exercises_count": 24,
  "accuracy": 0.85,
  "stats": {
    "correct": 18,
    "partial": 4,
    "incorrect": 2
  },
  "created_at": "2025-01-01T12:00:00Z"
}
```

#### PATCH /api/topics/{topic_id}

Обновить тему.

**Request:**
```json
{
  "name": "Pretérito Perfecto (обновлено)",
  "description": "Прошедшее совершенное время"
}
```

**Response 200:**
```json
{
  "id": "uuid",
  "name": "Pretérito Perfecto (обновлено)",
  ...
}
```

**Errors:**
- `403 FORBIDDEN` - Нельзя редактировать групповую тему

#### DELETE /api/topics/{topic_id}

Удалить тему.

**Response 204 No Content**

**Errors:**
- `403 FORBIDDEN` - Нельзя удалить групповую тему

#### POST /api/topics/{topic_id}/activate

Установить тему как активную.

**Response 200:**
```json
{
  "id": "uuid",
  "is_active": true,
  ...
}
```

#### POST /api/topics/suggest

Получить рекомендованные темы от LLM.

**Request:**
```json
{
  "profile_id": "uuid"
}
```

**Response 200:**
```json
{
  "suggestions": [
    {
      "name": "Pretérito Perfecto",
      "description": "Прошедшее время для недавних действий",
      "type": "grammar",
      "reason": "Соответствует вашему уровню A2 и цели 'работа'",
      "examples": ["He trabajado", "Has comido"]
    },
    {
      "name": "Еда и рестораны",
      "description": "Лексика для заказа в ресторане",
      "type": "vocabulary",
      "reason": "Полезно для путешествий"
    }
  ]
}
```

---

### 8. Exercises

#### POST /api/exercises/generate

Сгенерировать упражнение.

**Request:**
```json
{
  "topic_id": "uuid",
  "type": "free_text"
}
```

**Values:** `"free_text"`, `"multiple_choice"`

**Response 200:**
```json
{
  "id": "uuid",
  "topic_id": "uuid",
  "type": "free_text",
  "question": "Переведите на испанский:",
  "prompt": "Я работал в этой компании два года",
  "hint": null,
  "metadata": {
    "difficulty": "medium"
  }
}
```

**For multiple_choice:**
```json
{
  "id": "uuid",
  "topic_id": "uuid",
  "type": "multiple_choice",
  "question": "Выберите правильную форму глагола:",
  "prompt": "Yo ____ en esta empresa dos años",
  "options": [
    "trabajo",
    "trabajé",
    "he trabajado",
    "trabajaba"
  ],
  "correct_index": 2,
  "metadata": {}
}
```

**Errors:**
- `400 LIMIT_REACHED` - Достигнут дневной лимит упражнений
- `402 PAYMENT_REQUIRED` - Требуется премиум

#### POST /api/exercises/{exercise_id}/submit

Отправить ответ на упражнение.

**Request:**
```json
{
  "answer": "He trabajado en esta empresa dos años",
  "used_hint": false
}
```

**Response 200:**
```json
{
  "result": "correct",
  "correct_answer": "He trabajado en esta empresa dos años",
  "explanation": "Правильно! Используется Pretérito Perfecto, так как действие связано с настоящим (два года = до сих пор).",
  "alternatives": [
    "Trabajé en esta empresa dos años"
  ],
  "feedback": "Отлично! Вы правильно выбрали время."
}
```

**Values for `result`:** `"correct"`, `"partial"`, `"incorrect"`

#### POST /api/exercises/{exercise_id}/hint

Получить подсказку.

**Response 200:**
```json
{
  "hint": "Подумайте, связано ли действие с настоящим моментом?"
}
```

#### GET /api/exercises/history

История выполненных упражнений.

**Query params:**
- `topic_id` (optional)
- `profile_id` (optional)
- `limit`, `offset`

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "topic_id": "uuid",
      "topic_name": "Pretérito Perfecto",
      "type": "free_text",
      "question": "...",
      "user_answer": "...",
      "result": "correct",
      "used_hint": false,
      "duration_seconds": 45,
      "completed_at": "2025-01-08T12:00:00Z"
    }
  ],
  "pagination": {...}
}
```

---

### 9. Groups

#### GET /api/groups

Список групп пользователя.

**Query params:**
- `role` (optional) - `owner`, `member` (по умолчанию: все)

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "owner_id": "uuid",
      "owner_name": "Maria",
      "name": "Испанский A2 2025",
      "description": "Группа для начинающих",
      "role": "owner",
      "members_count": 12,
      "max_members": 100,
      "materials_count": 8,
      "created_at": "2025-01-01T12:00:00Z"
    },
    {
      "id": "uuid",
      "owner_id": "uuid",
      "owner_name": "John",
      "name": "Грамматика испанского",
      "role": "member",
      "members_count": 25,
      "max_members": 100,
      "created_at": "2024-12-01T12:00:00Z"
    }
  ]
}
```

#### POST /api/groups

Создать группу.

**Request:**
```json
{
  "name": "Испанский для путешествий",
  "description": "Практическая лексика для поездок"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "owner_id": "uuid",
  "name": "Испанский для путешествий",
  "description": "Практическая лексика для поездок",
  "members_count": 1,
  "max_members": 5,
  "created_at": "2025-01-08T12:00:00Z"
}
```

**Errors:**
- `400 LIMIT_REACHED` - Достигнут лимит групп (1 для free)
- `402 PAYMENT_REQUIRED` - Требуется премиум

#### GET /api/groups/{group_id}

Получить детали группы.

**Response 200:**
```json
{
  "id": "uuid",
  "owner_id": "uuid",
  "owner_name": "Maria",
  "name": "Испанский A2 2025",
  "description": "Группа для начинающих",
  "role": "owner",
  "members_count": 12,
  "max_members": 100,
  "created_at": "2025-01-01T12:00:00Z"
}
```

#### PATCH /api/groups/{group_id}

Обновить группу.

**Request:**
```json
{
  "name": "Испанский A2 2025 (обновлено)",
  "description": "Обновленное описание"
}
```

**Response 200:**
```json
{
  "id": "uuid",
  "name": "Испанский A2 2025 (обновлено)",
  ...
}
```

**Errors:**
- `403 FORBIDDEN` - Только владелец может редактировать

#### DELETE /api/groups/{group_id}

Удалить группу.

**Response 204 No Content**

**Errors:**
- `403 FORBIDDEN` - Только владелец может удалить

#### GET /api/groups/{group_id}/members

Список участников группы.

**Response 200:**
```json
{
  "data": [
    {
      "user_id": "uuid",
      "telegram_id": 123456789,
      "first_name": "Maria",
      "username": "maria",
      "role": "owner",
      "joined_at": "2025-01-01T12:00:00Z"
    },
    {
      "user_id": "uuid",
      "telegram_id": 987654321,
      "first_name": "John",
      "username": "john",
      "role": "member",
      "joined_at": "2025-01-05T12:00:00Z"
    }
  ]
}
```

#### POST /api/groups/{group_id}/members

Пригласить участника в группу.

**Request:**
```json
{
  "user_identifier": "@johndoe"
}
```

**Values:** username (`@johndoe`), telegram_id (`123456789`), или Telegram profile link

**Response 201:**
```json
{
  "invite_id": "uuid",
  "user_id": "uuid",
  "user_name": "John",
  "status": "pending",
  "expires_at": "2025-01-15T12:00:00Z",
  "created_at": "2025-01-08T12:00:00Z"
}
```

**Errors:**
- `400 LIMIT_REACHED` - Достигнут лимит участников
- `400 USER_NOT_FOUND` - Пользователь не найден в системе
- `400 ALREADY_MEMBER` - Пользователь уже участник
- `403 FORBIDDEN` - Только владелец может приглашать

#### DELETE /api/groups/{group_id}/members/{user_id}

Удалить участника из группы.

**Response 204 No Content**

**Errors:**
- `403 FORBIDDEN` - Только владелец может удалять
- `400 CANNOT_REMOVE_OWNER` - Нельзя удалить владельца

#### POST /api/groups/{group_id}/leave

Покинуть группу.

**Response 204 No Content**

**Errors:**
- `400 OWNER_CANNOT_LEAVE` - Владелец не может покинуть группу (сначала удалите)

#### GET /api/groups/{group_id}/invites

Список ожидающих приглашений (только для владельца).

**Response 200:**
```json
{
  "data": [
    {
      "invite_id": "uuid",
      "user_id": "uuid",
      "user_name": "Alice",
      "status": "pending",
      "expires_at": "2025-01-15T12:00:00Z",
      "created_at": "2025-01-08T12:00:00Z"
    }
  ]
}
```

#### DELETE /api/groups/invites/{invite_id}

Отозвать приглашение.

**Response 204 No Content**

#### POST /api/groups/invites/{invite_id}/accept

Принять приглашение.

**Response 200:**
```json
{
  "group_id": "uuid",
  "group_name": "Испанский A2 2025",
  "role": "member",
  "joined_at": "2025-01-08T12:00:00Z"
}
```

**Errors:**
- `400 INVITE_EXPIRED` - Приглашение истекло
- `404 INVITE_NOT_FOUND`

#### POST /api/groups/invites/{invite_id}/decline

Отклонить приглашение.

**Response 204 No Content**

#### GET /api/groups/{group_id}/materials

Список материалов группы.

**Query params:**
- `type` (optional) - `deck`, `topic`

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "type": "deck",
      "name": "Времена испанского",
      "description": null,
      "owner_id": "uuid",
      "owner_name": "Maria",
      "cards_count": 120,
      "shared_at": "2025-01-05T12:00:00Z"
    },
    {
      "id": "uuid",
      "type": "topic",
      "name": "Pretérito Perfecto",
      "description": "Прошедшее время",
      "owner_id": "uuid",
      "owner_name": "Maria",
      "exercises_count": 24,
      "shared_at": "2025-01-06T12:00:00Z"
    }
  ]
}
```

#### POST /api/groups/{group_id}/materials

Добавить материалы в группу.

**Request:**
```json
{
  "material_ids": ["uuid1", "uuid2"],
  "type": "deck"
}
```

**Values:** `"deck"`, `"topic"`

**Response 201:**
```json
{
  "added": [
    {
      "id": "uuid1",
      "type": "deck",
      "name": "Времена испанского"
    }
  ],
  "already_shared": [],
  "failed": []
}
```

**Errors:**
- `403 FORBIDDEN` - Только владелец может добавлять материалы

#### DELETE /api/groups/{group_id}/materials/{material_id}

Убрать материал из группы.

**Query params:**
- `type` (required) - `deck`, `topic`

**Response 204 No Content**

**Errors:**
- `403 FORBIDDEN` - Только владелец может удалять материалы

#### GET /api/groups/{group_id}/members/{user_id}/progress

Прогресс участника по материалам группы (только для владельца).

**Response 200:**
```json
{
  "user_id": "uuid",
  "user_name": "John",
  "decks": [
    {
      "deck_id": "uuid",
      "deck_name": "Времена испанского",
      "total_cards": 120,
      "studied_cards": 45,
      "progress": 0.375,
      "stats": {
        "know": 30,
        "repeat": 10,
        "dont_know": 5
      },
      "last_activity": "2025-01-08T10:00:00Z"
    }
  ],
  "topics": [
    {
      "topic_id": "uuid",
      "topic_name": "Pretérito Perfecto",
      "exercises_completed": 15,
      "accuracy": 0.80,
      "stats": {
        "correct": 12,
        "partial": 2,
        "incorrect": 1
      },
      "last_activity": "2025-01-08T11:00:00Z"
    }
  ]
}
```

---

### 10. Stats

#### GET /api/stats

Общая статистика пользователя.

**Query params:**
- `profile_id` (optional) - если не указан, используется активный профиль
- `period` (optional) - `week`, `month`, `3months`, `year`, `all` (default: `month`)

**Response 200:**
```json
{
  "profile_id": "uuid",
  "language": "es",
  "current_level": "A2",
  "period": "month",
  "streak": {
    "current": 12,
    "best": 45,
    "total_days": 89
  },
  "cards": {
    "total": 124,
    "studied": 95,
    "new": 29,
    "stats": {
      "know": 60,
      "repeat": 20,
      "dont_know": 15
    }
  },
  "exercises": {
    "total": 48,
    "stats": {
      "correct": 38,
      "partial": 7,
      "incorrect": 3
    },
    "accuracy": 0.79
  },
  "time": {
    "total_minutes": 456,
    "average_per_day": 15
  },
  "activity": [
    {
      "date": "2025-01-08",
      "cards_studied": 10,
      "exercises_completed": 3,
      "time_minutes": 20
    },
    ...
  ]
}
```

#### GET /api/stats/streak

Информация о стрике.

**Query params:**
- `profile_id` (optional)

**Response 200:**
```json
{
  "profile_id": "uuid",
  "current_streak": 12,
  "best_streak": 45,
  "total_active_days": 89,
  "today_completed": true,
  "last_activity": "2025-01-08T14:30:00Z",
  "streak_safe_until": "2025-01-09T00:00:00Z"
}
```

#### GET /api/stats/calendar

Календарь активности (для визуализации).

**Query params:**
- `profile_id` (optional)
- `weeks` (optional, default: 12) - количество недель

**Response 200:**
```json
{
  "data": [
    {
      "date": "2025-01-08",
      "activity_level": "high",
      "cards_studied": 15,
      "exercises_completed": 5,
      "time_minutes": 25
    },
    ...
  ]
}
```

**Values for `activity_level`:** `"none"`, `"low"`, `"medium"`, `"high"`

---

### 11. Subscriptions

#### GET /api/subscriptions/status

Статус подписки пользователя.

**Response 200:**
```json
{
  "is_premium": true,
  "status": "active",
  "plan": "yearly",
  "price": "49.00",
  "currency": "EUR",
  "current_period_start": "2025-01-01T00:00:00Z",
  "current_period_end": "2026-01-01T00:00:00Z",
  "cancel_at_period_end": false,
  "payment_method": {
    "type": "card",
    "last4": "4242",
    "brand": "visa"
  }
}
```

**For free users:**
```json
{
  "is_premium": false,
  "status": "free",
  "trial_available": false,
  "trial_used": true,
  "trial_ended_at": "2025-01-08T00:00:00Z"
}
```

#### POST /api/subscriptions/create-checkout

Создать Stripe Checkout Session.

**Request:**
```json
{
  "plan": "yearly",
  "success_url": "https://t.me/bot?start=payment_success",
  "cancel_url": "https://t.me/bot?start=payment_cancel"
}
```

**Values:** `"monthly"`, `"yearly"`

**Response 200:**
```json
{
  "checkout_session_id": "cs_xxx",
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_xxx"
}
```

#### POST /api/subscriptions/cancel

Отменить подписку.

**Response 200:**
```json
{
  "status": "active",
  "cancel_at_period_end": true,
  "current_period_end": "2026-01-01T00:00:00Z",
  "message": "Подписка будет отменена 1 января 2026"
}
```

#### POST /api/subscriptions/reactivate

Возобновить подписку (если была отменена, но период еще не истек).

**Response 200:**
```json
{
  "status": "active",
  "cancel_at_period_end": false,
  "message": "Подписка возобновлена"
}
```

#### GET /api/subscriptions/invoices

История платежей.

**Query params:**
- `limit`, `offset`

**Response 200:**
```json
{
  "data": [
    {
      "id": "in_xxx",
      "amount": "49.00",
      "currency": "EUR",
      "status": "paid",
      "created": "2025-01-01T00:00:00Z",
      "invoice_pdf": "https://pay.stripe.com/invoice/xxx/pdf"
    }
  ],
  "pagination": {...}
}
```

#### POST /api/subscriptions/webhook

Stripe webhook endpoint (для внутреннего использования).

**Headers:**
```
Stripe-Signature: xxx
```

**Events handled:**
- `checkout.session.completed`
- `invoice.paid`
- `invoice.payment_failed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

**Response 200:**
```json
{
  "received": true
}
```

---

### 12. Notifications

#### GET /api/notifications

Список уведомлений пользователя.

**Query params:**
- `unread_only` (optional, default: false)
- `limit`, `offset`

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "type": "streak_reminder",
      "title": "Не забудьте о стрике!",
      "message": "Сделайте хотя бы одно действие сегодня, чтобы сохранить стрик в 12 дней",
      "data": {
        "profile_id": "uuid",
        "streak": 12
      },
      "is_read": false,
      "created_at": "2025-01-08T18:00:00Z"
    },
    {
      "id": "uuid",
      "type": "group_invite",
      "title": "Приглашение в группу",
      "message": "Maria пригласил вас в группу 'Испанский A2 2025'",
      "data": {
        "invite_id": "uuid",
        "group_id": "uuid",
        "group_name": "Испанский A2 2025",
        "inviter_name": "Maria"
      },
      "is_read": false,
      "created_at": "2025-01-08T15:00:00Z"
    }
  ],
  "pagination": {...},
  "unread_count": 2
}
```

**Notification types:**
- `streak_reminder` - напоминание о стрике
- `group_invite` - приглашение в группу
- `group_material_added` - новые материалы в группе
- `subscription_expiring` - истечение подписки
- `achievement_unlocked` - разблокировано достижение

#### POST /api/notifications/{notification_id}/read

Отметить уведомление как прочитанное.

**Response 200:**
```json
{
  "id": "uuid",
  "is_read": true
}
```

#### POST /api/notifications/read-all

Отметить все уведомления как прочитанные.

**Response 200:**
```json
{
  "marked_read": 5
}
```

---

### 13. Admin (только для администраторов)

#### GET /api/admin/users

Список всех пользователей (с пагинацией и фильтрами).

**Query params:**
- `status` - `all`, `free`, `premium`
- `activity` - `active_7d`, `active_30d`, `inactive`
- `language` - фильтр по изучаемому языку
- `sort` - `created_at`, `last_activity`, `cards_count`
- `limit`, `offset`

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "telegram_id": 123456789,
      "first_name": "John",
      "username": "johndoe",
      "is_premium": true,
      "languages": ["es", "fr"],
      "cards_count": 124,
      "exercises_count": 48,
      "streak": 12,
      "last_activity": "2025-01-08T14:30:00Z",
      "created_at": "2024-12-01T12:00:00Z"
    }
  ],
  "pagination": {...}
}
```

**Errors:**
- `403 FORBIDDEN` - Требуется роль администратора

#### GET /api/admin/metrics

Агрегированные метрики системы.

**Query params:**
- `period` - `7d`, `30d`, `90d`, `all`

**Response 200:**
```json
{
  "period": "30d",
  "users": {
    "total": 1250,
    "new": 150,
    "active": 450,
    "premium": 85,
    "premium_percentage": 6.8
  },
  "retention": {
    "day_7": 0.65,
    "day_30": 0.42
  },
  "content": {
    "total_cards": 125000,
    "total_exercises": 48000,
    "total_groups": 45
  },
  "activity": {
    "messages_sent": 35000,
    "cards_studied": 95000,
    "exercises_completed": 28000,
    "average_session_minutes": 18
  },
  "revenue": {
    "total": "4215.00",
    "currency": "EUR",
    "subscriptions_active": 85
  }
}
```

#### GET /api/admin/users/{user_id}

Детальная информация о пользователе.

**Response 200:**
```json
{
  "id": "uuid",
  "telegram_id": 123456789,
  "first_name": "John",
  "username": "johndoe",
  "is_premium": true,
  "subscription": {...},
  "profiles": [...],
  "stats": {
    "cards_count": 124,
    "exercises_count": 48,
    "streak": 12,
    "groups_owned": 1,
    "groups_member": 2
  },
  "activity_log": [
    {
      "date": "2025-01-08",
      "actions": ["card_added", "exercise_completed"],
      "time_minutes": 20
    }
  ],
  "created_at": "2024-12-01T12:00:00Z",
  "last_activity": "2025-01-08T14:30:00Z"
}
```

#### POST /api/admin/users/{user_id}/premium

Вручную активировать премиум для пользователя.

**Request:**
```json
{
  "duration_days": 30,
  "reason": "Compensation for bug"
}
```

**Values:** `duration_days` от 1 до 365, или `"unlimited"`

**Response 200:**
```json
{
  "user_id": "uuid",
  "is_premium": true,
  "expires_at": "2025-02-08T00:00:00Z",
  "reason": "Compensation for bug"
}
```

#### POST /api/admin/users/{user_id}/message

Отправить сообщение пользователю (через бота).

**Request:**
```json
{
  "message": "Привет! Мы исправили ошибку, о которой вы сообщали."
}
```

**Response 200:**
```json
{
  "sent": true,
  "message_id": "123456"
}
```

---

## Модели данных (API Contracts)

### User
```typescript
interface User {
  id: string;                    // UUID
  telegram_id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  is_premium: boolean;
  subscription?: Subscription;
  limits: UserLimits;
  created_at: string;            // ISO 8601
  updated_at: string;
}

interface UserLimits {
  profiles: { used: number; max: number };
  messages: { used: number; max: number; reset_at: string };
  exercises: { used: number; max: number; reset_at: string };
  cards: { used: number; max: number };
  groups: { used: number; max: number };
}
```

### Language Profile
```typescript
interface LanguageProfile {
  id: string;
  user_id: string;
  language: string;              // ISO 639-1 code (e.g., "es", "fr")
  language_name: string;         // Локализованное название
  current_level: CEFRLevel;
  target_level: CEFRLevel;
  goals: string[];               // ["work", "travel", "study", etc.]
  interface_language: string;    // "ru" or learning language
  is_active: boolean;
  progress?: ProfileProgress;
  created_at: string;
  updated_at: string;
}

type CEFRLevel = "A1" | "A2" | "B1" | "B2" | "C1" | "C2";

interface ProfileProgress {
  cards_count: number;
  exercises_count: number;
  streak: number;
}
```

### Deck
```typescript
interface Deck {
  id: string;
  profile_id: string;
  name: string;
  description?: string;
  is_active: boolean;
  is_group: boolean;             // Групповая колода
  owner_id?: string;             // Если групповая
  owner_name?: string;
  cards_count: number;
  new_cards_count: number;
  due_cards_count: number;
  stats?: DeckStats;
  created_at: string;
  updated_at: string;
}

interface DeckStats {
  know: number;
  repeat: number;
  dont_know: number;
  new: number;
}
```

### Card
```typescript
interface Card {
  id: string;
  deck_id: string;
  word: string;                  // Слово на изучаемом языке
  translation: string;           // Перевод на русский
  example: string;               // Пример использования
  example_translation: string;
  lemma: string;                 // Начальная форма (для проверки дубликатов)
  status: CardStatus;
  interval_days: number;         // Интервал повторения
  next_review: string;           // Дата следующего повторения
  reviews_count: number;
  last_rating?: CardRating;
  history?: CardReview[];
  created_at: string;
}

type CardStatus = "new" | "learning" | "review";
type CardRating = "know" | "repeat" | "dont_know";

interface CardReview {
  date: string;
  rating: CardRating;
  interval_before: number;
  interval_after: number;
}
```

### Topic
```typescript
interface Topic {
  id: string;
  profile_id: string;
  name: string;
  description: string;
  type: TopicType;
  is_active: boolean;
  is_group: boolean;
  owner_id?: string;
  owner_name?: string;
  exercises_count: number;
  accuracy: number;              // 0.0 - 1.0
  stats?: TopicStats;
  created_at: string;
  updated_at: string;
}

type TopicType = "grammar" | "vocabulary" | "situation";

interface TopicStats {
  correct: number;
  partial: number;
  incorrect: number;
}
```

### Exercise
```typescript
interface Exercise {
  id: string;
  topic_id: string;
  type: ExerciseType;
  question: string;
  prompt: string;
  hint?: string;
  options?: string[];            // Для multiple_choice
  correct_index?: number;        // Для multiple_choice
  metadata: Record<string, any>;
}

type ExerciseType = "free_text" | "multiple_choice";

interface ExerciseResult {
  result: ExerciseResultType;
  correct_answer: string;
  explanation: string;
  alternatives?: string[];
  feedback: string;
}

type ExerciseResultType = "correct" | "partial" | "incorrect";
```

### Group
```typescript
interface Group {
  id: string;
  owner_id: string;
  owner_name: string;
  name: string;
  description?: string;
  role: GroupRole;               // Роль текущего пользователя
  members_count: number;
  max_members: number;
  materials_count?: number;
  created_at: string;
  updated_at: string;
}

type GroupRole = "owner" | "member";

interface GroupMember {
  user_id: string;
  telegram_id: number;
  first_name: string;
  username?: string;
  role: GroupRole;
  joined_at: string;
}

interface GroupMaterial {
  id: string;                    // ID материала (deck или topic)
  type: MaterialType;
  name: string;
  description?: string;
  owner_id: string;
  owner_name: string;
  cards_count?: number;          // Если deck
  exercises_count?: number;      // Если topic
  shared_at: string;
}

type MaterialType = "deck" | "topic";
```

### Subscription
```typescript
interface Subscription {
  status: SubscriptionStatus;
  plan?: SubscriptionPlan;
  price?: string;
  currency?: string;
  current_period_start?: string;
  current_period_end?: string;
  cancel_at_period_end: boolean;
  payment_method?: PaymentMethod;
  trial_ends_at?: string;
}

type SubscriptionStatus = "free" | "trial" | "active" | "canceled" | "expired";
type SubscriptionPlan = "monthly" | "yearly";

interface PaymentMethod {
  type: "card";
  last4: string;
  brand: string;                 // "visa", "mastercard", etc.
}
```

### Notification
```typescript
interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  data: Record<string, any>;     // Дополнительные данные
  is_read: boolean;
  created_at: string;
}

type NotificationType =
  | "streak_reminder"
  | "group_invite"
  | "group_material_added"
  | "subscription_expiring"
  | "achievement_unlocked";
```

### Stats
```typescript
interface UserStats {
  profile_id: string;
  language: string;
  current_level: CEFRLevel;
  period: StatsPeriod;
  streak: StreakInfo;
  cards: CardStats;
  exercises: ExerciseStats;
  time: TimeStats;
  activity: ActivityDay[];
}

type StatsPeriod = "week" | "month" | "3months" | "year" | "all";

interface StreakInfo {
  current: number;
  best: number;
  total_days: number;
}

interface CardStats {
  total: number;
  studied: number;
  new: number;
  stats: {
    know: number;
    repeat: number;
    dont_know: number;
  };
}

interface ExerciseStats {
  total: number;
  stats: {
    correct: number;
    partial: number;
    incorrect: number;
  };
  accuracy: number;
}

interface TimeStats {
  total_minutes: number;
  average_per_day: number;
}

interface ActivityDay {
  date: string;                  // YYYY-MM-DD
  cards_studied: number;
  exercises_completed: number;
  time_minutes: number;
}
```

---

## Обработка ошибок

### Формат ответа при ошибке

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Человекочитаемое сообщение на языке интерфейса",
    "details": {
      "field": "Дополнительная информация"
    }
  }
}
```

### HTTP статусы

- **200 OK** - Успешный запрос
- **201 Created** - Ресурс создан
- **204 No Content** - Успешно, без тела ответа
- **400 Bad Request** - Ошибка валидации или бизнес-логики
- **401 Unauthorized** - Требуется аутентификация
- **403 Forbidden** - Нет прав доступа
- **404 Not Found** - Ресурс не найден
- **409 Conflict** - Конфликт (например, дубликат)
- **422 Unprocessable Entity** - Ошибка валидации данных
- **429 Too Many Requests** - Превышен rate limit
- **500 Internal Server Error** - Внутренняя ошибка сервера
- **502 Bad Gateway** - Ошибка внешнего сервиса (LLM, Stripe)
- **503 Service Unavailable** - Сервис временно недоступен

### Коды ошибок

#### Authentication & Authorization (4xx)
- `INVALID_INIT_DATA` (400) - Невалидный initData
- `AUTH_FAILED` (401) - Ошибка аутентификации
- `TOKEN_EXPIRED` (401) - JWT токен истек
- `FORBIDDEN` (403) - Нет прав доступа
- `RATE_LIMIT_EXCEEDED` (429) - Превышен лимит запросов

#### Validation (400, 422)
- `VALIDATION_ERROR` (422) - Ошибка валидации полей
- `INVALID_LEVEL` (400) - Неверный CEFR уровень
- `TARGET_BELOW_CURRENT` (400) - Целевой уровень ниже текущего
- `INVALID_FIELD_VALUE` (400) - Неверное значение поля

#### Resources (404, 409)
- `USER_NOT_FOUND` (404)
- `PROFILE_NOT_FOUND` (404)
- `DECK_NOT_FOUND` (404)
- `CARD_NOT_FOUND` (404)
- `TOPIC_NOT_FOUND` (404)
- `GROUP_NOT_FOUND` (404)
- `INVITE_NOT_FOUND` (404)
- `DUPLICATE_LEMMA` (409) - Карточка с такой леммой уже существует
- `DUPLICATE_LANGUAGE` (400) - Профиль для этого языка уже существует
- `ALREADY_MEMBER` (400) - Пользователь уже участник группы

#### Business Logic (400)
- `LIMIT_REACHED` (400) - Достигнут лимит (профилей, карточек, групп и т.д.)
- `LAST_PROFILE` (400) - Нельзя удалить последний профиль
- `LAST_DECK` (400) - Нельзя удалить единственную колоду
- `CANNOT_REMOVE_OWNER` (400) - Нельзя удалить владельца группы
- `OWNER_CANNOT_LEAVE` (400) - Владелец не может покинуть группу
- `INVITE_EXPIRED` (400) - Приглашение истекло
- `TOO_MANY_WORDS` (400) - Слишком много слов (>20)

#### Payment (402)
- `PAYMENT_REQUIRED` (402) - Требуется премиум подписка
- `SUBSCRIPTION_REQUIRED` (402) - Функция доступна только для премиум

#### Transport & Infrastructure (4xx/5xx)
- `NOT_FOUND` (404) - Маршрут или ресурс не найден
- `METHOD_NOT_ALLOWED` (405) - HTTP метод не поддерживается данным endpoint
- `PAYLOAD_TOO_LARGE` (413) - Превышен допустимый размер тела запроса
- `CONFLICT` (409) - Общий конфликт запроса, когда нет более точного кода

#### External Services (502, 503)
- `LLM_SERVICE_ERROR` (502) - Ошибка LLM сервиса
- `STRIPE_ERROR` (502) - Ошибка Stripe API
- `SERVICE_UNAVAILABLE` (503) - Сервис временно недоступен

#### Internal (500)
- `INTERNAL_ERROR` (500) - Внутренняя ошибка сервера
- `DATABASE_ERROR` (500) - Ошибка базы данных

### Примеры ответов с ошибками

**Validation error:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Ошибка валидации",
    "details": {
      "name": "Название обязательно",
      "current_level": "Неверный CEFR уровень"
    }
  }
}
```

**Rate limit exceeded:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Превышен лимит запросов. Попробуйте через 42 секунды.",
    "retry_after": 42
  }
}
```

**Limit reached:**
```json
{
  "error": {
    "code": "LIMIT_REACHED",
    "message": "Достигнут лимит профилей (1 для бесплатного плана)",
    "details": {
      "limit_type": "profiles",
      "current": 1,
      "max": 1,
      "upgrade_url": "/profile/premium"
    }
  }
}
```

**Payment required:**
```json
{
  "error": {
    "code": "PAYMENT_REQUIRED",
    "message": "Эта функция доступна только для премиум пользователей",
    "details": {
      "feature": "unlimited_cards",
      "upgrade_url": "/profile/premium"
    }
  }
}
```

---

## Security Headers

```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

---

Этот документ описывает полную спецификацию REST API для Telegram-бота изучения языков с ИИ-преподавателем, включая все endpoints, модели данных, обработку ошибок и безопасность.
