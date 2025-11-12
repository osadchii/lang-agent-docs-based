# База данных

## СУБД

**PostgreSQL 15+**

**Причины выбора:**
- Отличная поддержка JSON для хранения динамических данных (goals, metadata)
- JSONB индексы для быстрого поиска
- Надежность и ACID транзакции
- Полнотекстовый поиск для карточек
- Поддержка UUID как primary key
- Богатая экосистема инструментов
- Бесплатное использование

**Альтернативы (не выбраны):**
- MySQL - меньше возможностей для JSON
- MongoDB - нет транзакций (critical для финансов), сложнее с отношениями

---

## Общие принципы

### Naming Convention

**Таблицы:** `snake_case`, множественное число (`users`, `language_profiles`)
**Колонки:** `snake_case` (`first_name`, `created_at`)
**Primary keys:** `id` (UUID)
**Foreign keys:** `{table_name}_id` (`user_id`, `deck_id`)
**Timestamps:** `created_at`, `updated_at`
**Soft delete:** `deleted` (boolean) + `deleted_at` (timestamp)

### Primary Keys

**Используем UUID везде:**
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

**Преимущества:**
- Невозможно перебрать все ID (безопасность)
- Можно генерировать на клиенте без конфликтов
- Распределенные системы (если понадобится масштабирование)

**Недостатки (некритичны для нашего проекта):**
- Больше места (16 байт vs 4-8 байт)
- Чуть медленнее индексация

### Timestamps

**Все таблицы имеют:**
```sql
created_at TIMESTAMP NOT NULL DEFAULT NOW()
updated_at TIMESTAMP NOT NULL DEFAULT NOW()
```

**Trigger для auto-update:**
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Soft Delete

**Для важных данных используем soft delete:**
```sql
deleted BOOLEAN NOT NULL DEFAULT FALSE
deleted_at TIMESTAMP
```

**Преимущества:**
- Возможность восстановления
- Сохранение истории для аналитики
- GDPR compliance (можно hard delete позже)

**Таблицы с soft delete:**
- `users`
- `language_profiles`
- `decks`
- `cards`
- `topics`
- `groups`

---

## Схема БД

### Таблица: users

**Описание:** Основная таблица пользователей

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT NOT NULL UNIQUE,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255),
    username VARCHAR(255),

    -- Subscription
    is_premium BOOLEAN NOT NULL DEFAULT FALSE,
    premium_expires_at TIMESTAMP,
    trial_ends_at TIMESTAMP,
    trial_used BOOLEAN NOT NULL DEFAULT FALSE,

    -- Admin
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,

    -- Settings
    timezone VARCHAR(50) DEFAULT 'UTC',
    language_code VARCHAR(10),

    -- Soft delete
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_activity TIMESTAMP
);

-- Индексы
CREATE UNIQUE INDEX idx_users_telegram_id ON users(telegram_id) WHERE deleted = FALSE;
CREATE INDEX idx_users_is_premium ON users(is_premium) WHERE deleted = FALSE;
CREATE INDEX idx_users_last_activity ON users(last_activity) WHERE deleted = FALSE;
CREATE INDEX idx_users_created_at ON users(created_at);

-- Trigger для updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Примечания:**
- `telegram_id` - основной идентификатор от Telegram (BIGINT, т.к. может быть большим числом)
- `is_premium` - флаг премиум статуса
- `trial_ends_at` - дата окончания триала (7 дней для новых пользователей)
- `trial_used` - уже использовал триал (нельзя повторно)
- `timezone` - часовой пояс для напоминаний о стрике
- `last_activity` - для retention метрик

---

### Таблица: language_profiles

**Описание:** Языковые профили пользователей (каждый пользователь может изучать несколько языков)

```sql
CREATE TABLE language_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Language info
    language VARCHAR(10) NOT NULL,  -- ISO 639-1 код (es, fr, de, etc.)
    language_name VARCHAR(100) NOT NULL,  -- Локализованное название

    -- Levels (CEFR)
    current_level VARCHAR(2) NOT NULL CHECK (current_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')),
    target_level VARCHAR(2) NOT NULL CHECK (target_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')),

    -- Goals (JSON array)
    goals JSONB NOT NULL DEFAULT '[]',  -- ["work", "travel", "study", ...]

    -- Interface language
    interface_language VARCHAR(10) NOT NULL DEFAULT 'ru',

    -- Active profile
    is_active BOOLEAN NOT NULL DEFAULT FALSE,

    -- Progress
    streak INT NOT NULL DEFAULT 0,
    best_streak INT NOT NULL DEFAULT 0,
    total_active_days INT NOT NULL DEFAULT 0,
    last_activity_date DATE,

    -- Soft delete
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_target_level CHECK (
        CASE target_level
            WHEN 'A1' THEN current_level = 'A1'
            WHEN 'A2' THEN current_level IN ('A1', 'A2')
            WHEN 'B1' THEN current_level IN ('A1', 'A2', 'B1')
            WHEN 'B2' THEN current_level IN ('A1', 'A2', 'B1', 'B2')
            WHEN 'C1' THEN current_level IN ('A1', 'A2', 'B1', 'B2', 'C1')
            WHEN 'C2' THEN TRUE
        END
    )
);

-- Индексы
CREATE INDEX idx_profiles_user_id ON language_profiles(user_id) WHERE deleted = FALSE;
CREATE INDEX idx_profiles_user_active ON language_profiles(user_id, is_active) WHERE deleted = FALSE;
CREATE INDEX idx_profiles_language ON language_profiles(language) WHERE deleted = FALSE;
CREATE INDEX idx_profiles_last_activity ON language_profiles(last_activity_date) WHERE deleted = FALSE;

-- Уникальность: один язык на пользователя
CREATE UNIQUE INDEX idx_profiles_user_language ON language_profiles(user_id, language) WHERE deleted = FALSE;

-- Trigger для updated_at
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON language_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Constraint: только один активный профиль на пользователя
CREATE UNIQUE INDEX idx_profiles_one_active_per_user ON language_profiles(user_id, is_active)
    WHERE is_active = TRUE AND deleted = FALSE;
```

**Примечания:**
- `language` - ISO 639-1 код (es, fr, de, en, etc.)
- `goals` - JSONB массив целей: ["work", "travel", "study", "communication", "reading", "self_development", "relationships", "relocation"]
- `streak` - текущий стрик (дни обучения подряд)
- `last_activity_date` - для подсчета стрика (только дата, без времени)
- Constraint гарантирует target_level >= current_level

---

### Таблица: decks

**Описание:** Колоды карточек

```sql
CREATE TABLE decks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES language_profiles(id) ON DELETE CASCADE,

    -- Deck info
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Active deck (для выбора карточек в боте)
    is_active BOOLEAN NOT NULL DEFAULT FALSE,

    -- Group deck
    is_group BOOLEAN NOT NULL DEFAULT FALSE,
    owner_id UUID REFERENCES users(id) ON DELETE SET NULL,  -- Если групповая

    -- Stats (денормализация для производительности)
    cards_count INT NOT NULL DEFAULT 0,
    new_cards_count INT NOT NULL DEFAULT 0,
    due_cards_count INT NOT NULL DEFAULT 0,

    -- Soft delete
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_decks_profile_id ON decks(profile_id) WHERE deleted = FALSE;
CREATE INDEX idx_decks_profile_active ON decks(profile_id, is_active) WHERE deleted = FALSE;
CREATE INDEX idx_decks_is_group ON decks(is_group) WHERE deleted = FALSE;
CREATE INDEX idx_decks_owner_id ON decks(owner_id) WHERE deleted = FALSE;

-- Trigger
CREATE TRIGGER update_decks_updated_at BEFORE UPDATE ON decks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Constraint: только одна активная колода на профиль
CREATE UNIQUE INDEX idx_decks_one_active_per_profile ON decks(profile_id, is_active)
    WHERE is_active = TRUE AND deleted = FALSE;
```

**Примечания:**
- `is_group` - групповая колода (создана владельцем группы и расшарена)
- `owner_id` - владелец групповой колоды (NULL для личных колод)
- Счетчики cards_count обновляются триггерами при изменении cards

---

### Таблица: cards

**Описание:** Карточки для изучения слов

```sql
CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deck_id UUID NOT NULL REFERENCES decks(id) ON DELETE CASCADE,

    -- Card content
    word VARCHAR(200) NOT NULL,  -- Слово на изучаемом языке
    translation VARCHAR(200) NOT NULL,  -- Перевод на русский
    example TEXT NOT NULL,  -- Пример использования
    example_translation TEXT NOT NULL,  -- Перевод примера
    lemma VARCHAR(200) NOT NULL,  -- Начальная форма (для проверки дубликатов)
    notes TEXT,  -- Дополнительные заметки от LLM

    -- Spaced repetition (SM-2 inspired)
    status VARCHAR(20) NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'learning', 'review')),
    interval_days INT NOT NULL DEFAULT 0,
    next_review TIMESTAMP NOT NULL DEFAULT NOW(),
    reviews_count INT NOT NULL DEFAULT 0,
    ease_factor DECIMAL(3, 2) NOT NULL DEFAULT 2.50,  -- Для будущего (сейчас не используется)

    -- Last review
    last_rating VARCHAR(20) CHECK (last_rating IN ('know', 'repeat', 'dont_know')),
    last_reviewed_at TIMESTAMP,

    -- Soft delete
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_cards_deck_id ON cards(deck_id) WHERE deleted = FALSE;
CREATE INDEX idx_cards_status ON cards(status) WHERE deleted = FALSE;
CREATE INDEX idx_cards_next_review ON cards(next_review) WHERE deleted = FALSE;
CREATE INDEX idx_cards_lemma ON cards(lemma) WHERE deleted = FALSE;

-- Unique lemma per deck (проверка дубликатов)
CREATE UNIQUE INDEX idx_cards_deck_lemma ON cards(deck_id, LOWER(lemma)) WHERE deleted = FALSE;

-- Полнотекстовый поиск
CREATE INDEX idx_cards_word_search ON cards USING gin(to_tsvector('russian', word || ' ' || translation));

-- Trigger
CREATE TRIGGER update_cards_updated_at BEFORE UPDATE ON cards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Примечания:**
- `lemma` - начальная форма слова (для дубликатов: "лето" = "летом")
- `status` - new (никогда не изучалась), learning (изучается), review (на повторении)
- `interval_days` - интервал до следующего повторения
- `next_review` - дата/время следующего повторения
- Unique index на `(deck_id, lemma)` предотвращает дубликаты

---

### Таблица: card_reviews

**Описание:** История оценок карточек

```sql
CREATE TABLE card_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Review info
    rating VARCHAR(20) NOT NULL CHECK (rating IN ('know', 'repeat', 'dont_know')),

    -- Intervals
    interval_before INT NOT NULL,  -- Интервал до оценки
    interval_after INT NOT NULL,  -- Интервал после оценки

    -- Duration
    duration_seconds INT,  -- Время на оценку

    -- Timestamp
    reviewed_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_card_reviews_card_id ON card_reviews(card_id);
CREATE INDEX idx_card_reviews_user_id ON card_reviews(user_id);
CREATE INDEX idx_card_reviews_reviewed_at ON card_reviews(reviewed_at);
```

**Примечания:**
- История всех оценок карточек
- Используется для статистики и аналитики
- `duration_seconds` - для метрик (сколько времени пользователь думал)

---

### Таблица: topics

**Описание:** Темы для упражнений

```sql
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES language_profiles(id) ON DELETE CASCADE,

    -- Topic info
    name VARCHAR(200) NOT NULL,
    description TEXT,
    type VARCHAR(20) NOT NULL CHECK (type IN ('grammar', 'vocabulary', 'situation')),

    -- Active topic (для генерации упражнений в боте)
    is_active BOOLEAN NOT NULL DEFAULT FALSE,

    -- Group topic
    is_group BOOLEAN NOT NULL DEFAULT FALSE,
    owner_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Stats (денормализация)
    exercises_count INT NOT NULL DEFAULT 0,
    correct_count INT NOT NULL DEFAULT 0,
    partial_count INT NOT NULL DEFAULT 0,
    incorrect_count INT NOT NULL DEFAULT 0,
    accuracy DECIMAL(5, 2) NOT NULL DEFAULT 0.00,  -- 0.00 - 1.00

    -- Soft delete
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_topics_profile_id ON topics(profile_id) WHERE deleted = FALSE;
CREATE INDEX idx_topics_profile_active ON topics(profile_id, is_active) WHERE deleted = FALSE;
CREATE INDEX idx_topics_type ON topics(type) WHERE deleted = FALSE;
CREATE INDEX idx_topics_is_group ON topics(is_group) WHERE deleted = FALSE;

-- Trigger
CREATE TRIGGER update_topics_updated_at BEFORE UPDATE ON topics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Constraint: только одна активная тема на профиль
CREATE UNIQUE INDEX idx_topics_one_active_per_profile ON topics(profile_id, is_active)
    WHERE is_active = TRUE AND deleted = FALSE;
```

**Примечания:**
- `type` - тип темы: grammar (грамматика), vocabulary (лексика), situation (жизненная ситуация)
- `accuracy` - процент правильных ответов (0.00 - 1.00)
- Счетчики обновляются при создании exercise_history записей

---

### Таблица: exercise_history

**Описание:** История выполненных упражнений

```sql
CREATE TABLE exercise_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES language_profiles(id) ON DELETE CASCADE,

    -- Exercise content (сохраняем для истории)
    type VARCHAR(20) NOT NULL CHECK (type IN ('free_text', 'multiple_choice')),
    question TEXT NOT NULL,
    prompt TEXT NOT NULL,
    correct_answer TEXT NOT NULL,

    -- User answer
    user_answer TEXT NOT NULL,

    -- Result
    result VARCHAR(20) NOT NULL CHECK (result IN ('correct', 'partial', 'incorrect')),
    explanation TEXT,

    -- Metadata
    used_hint BOOLEAN NOT NULL DEFAULT FALSE,
    duration_seconds INT,

    -- Timestamp
    completed_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_exercise_history_user_id ON exercise_history(user_id);
CREATE INDEX idx_exercise_history_topic_id ON exercise_history(topic_id);
CREATE INDEX idx_exercise_history_profile_id ON exercise_history(profile_id);
CREATE INDEX idx_exercise_history_completed_at ON exercise_history(completed_at);
CREATE INDEX idx_exercise_history_result ON exercise_history(result);
```

**Примечания:**
- Упражнения генерируются динамически (не хранятся в БД до выполнения)
- Сохраняем только выполненные упражнения для истории
- `duration_seconds` - время выполнения
- `used_hint` - использовал ли подсказку

---

### Таблица: conversation_history

**Описание:** История диалогов с LLM

```sql
CREATE TABLE conversation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES language_profiles(id) ON DELETE CASCADE,

    -- Message
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,

    -- Tokens (для лимитов контекста)
    tokens INT NOT NULL DEFAULT 0,

    -- Timestamp
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_conversation_user_profile ON conversation_history(user_id, profile_id);
CREATE INDEX idx_conversation_timestamp ON conversation_history(timestamp);

-- Партиционирование по месяцам (для больших объемов данных)
-- ALTER TABLE conversation_history PARTITION BY RANGE (timestamp);
```

**Примечания:**
- `role` - кто отправил сообщение (user, assistant, system)
- `tokens` - количество токенов в сообщении (предвычислено)
- Используется для контекста LLM (последние 20 сообщений или 24 часа)
- В будущем можно партиционировать по времени

---

### Таблица: groups

**Описание:** Учебные группы

```sql
CREATE TABLE groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Group info
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Limits
    max_members INT NOT NULL DEFAULT 5,  -- 5 для free, 100 для premium

    -- Stats (денормализация)
    members_count INT NOT NULL DEFAULT 1,  -- Включая владельца

    -- Soft delete
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_groups_owner_id ON groups(owner_id) WHERE deleted = FALSE;

-- Trigger
CREATE TRIGGER update_groups_updated_at BEFORE UPDATE ON groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Примечания:**
- `owner_id` - создатель и владелец группы
- `max_members` - зависит от подписки владельца (5/100)
- `members_count` - включает владельца

---

### Таблица: group_members

**Описание:** Участники групп

```sql
CREATE TABLE group_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Role (пока только один уровень)
    role VARCHAR(20) NOT NULL DEFAULT 'member' CHECK (role IN ('member')),

    -- Timestamp
    joined_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_group_members_group_id ON group_members(group_id);
CREATE INDEX idx_group_members_user_id ON group_members(user_id);

-- Уникальность: один пользователь в группе только раз
CREATE UNIQUE INDEX idx_group_members_unique ON group_members(group_id, user_id);
```

**Примечания:**
- Владелец группы НЕ включен в эту таблицу (он в groups.owner_id)
- В v1.0 только один уровень прав (member)
- В v2.0 планируется добавить moderator role

---

### Таблица: group_invites

**Описание:** Приглашения в группы

```sql
CREATE TABLE group_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    inviter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    invitee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined', 'expired')),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL DEFAULT NOW() + INTERVAL '7 days',
    responded_at TIMESTAMP
);

-- Индексы
CREATE INDEX idx_group_invites_group_id ON group_invites(group_id);
CREATE INDEX idx_group_invites_invitee_id ON group_invites(invitee_id);
CREATE INDEX idx_group_invites_status ON group_invites(status);
CREATE INDEX idx_group_invites_expires_at ON group_invites(expires_at);

-- Уникальность: одно активное приглашение на пользователя в группу
CREATE UNIQUE INDEX idx_group_invites_unique_pending ON group_invites(group_id, invitee_id)
    WHERE status = 'pending';
```

**Примечания:**
- `inviter_id` - кто пригласил (владелец группы)
- `invitee_id` - кого пригласили
- `expires_at` - истекает через 7 дней
- Приглашения можно отозвать (статус изменится на 'expired')

---

### Таблица: group_materials

**Описание:** Связь групп с материалами (колоды, темы)

```sql
CREATE TABLE group_materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    material_id UUID NOT NULL,  -- ID колоды или темы
    material_type VARCHAR(20) NOT NULL CHECK (material_type IN ('deck', 'topic')),

    -- Timestamp
    shared_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_group_materials_group_id ON group_materials(group_id);
CREATE INDEX idx_group_materials_material_id_type ON group_materials(material_id, material_type);

-- Уникальность: один материал в группе только раз
CREATE UNIQUE INDEX idx_group_materials_unique ON group_materials(group_id, material_id, material_type);
```

**Примечания:**
- `material_type` - deck или topic
- `material_id` - UUID колоды или темы
- Polymorphic association (один материал может быть в нескольких группах)

---

### Таблица: subscriptions

**Описание:** Подписки пользователей (Stripe integration)

```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,

    -- Stripe
    stripe_customer_id VARCHAR(255) UNIQUE,
    stripe_subscription_id VARCHAR(255) UNIQUE,

    -- Subscription info
    status VARCHAR(20) NOT NULL CHECK (status IN ('free', 'trial', 'active', 'canceled', 'expired')),
    plan VARCHAR(20) CHECK (plan IN ('monthly', 'yearly')),

    -- Billing
    price DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'EUR',

    -- Periods
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,

    -- Cancellation
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    canceled_at TIMESTAMP,

    -- Payment method
    payment_method_type VARCHAR(50),
    payment_method_last4 VARCHAR(4),
    payment_method_brand VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_period_end ON subscriptions(current_period_end);

-- Trigger
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Примечания:**
- Один пользователь = одна подписка (UNIQUE на user_id)
- `stripe_customer_id` - ID в Stripe
- `stripe_subscription_id` - ID подписки в Stripe
- `status` - free (не оплачена), trial (триал), active (активна), canceled (отменена), expired (истекла)
- Обновляется через Stripe webhooks

---

### Таблица: notifications

**Описание:** Уведомления пользователей

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Notification content
    type VARCHAR(50) NOT NULL,  -- streak_reminder, group_invite, etc.
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSONB,  -- Дополнительные данные (group_id, invite_id, etc.)

    -- Status
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMP,

    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);
CREATE INDEX idx_notifications_type ON notifications(type);
```

**Примечания:**
- `type` - тип уведомления: streak_reminder, group_invite, group_material_added, subscription_expiring, achievement_unlocked
- `data` - JSONB с дополнительными данными (зависит от типа)
- Используется для Mini App (badge с количеством непрочитанных)

---

### Таблица: streak_reminders

**Описание:** Отслеживание отправленных напоминаний о стрике

```sql
CREATE TABLE streak_reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES language_profiles(id) ON DELETE CASCADE,

    -- Date (local time of user)
    sent_date DATE NOT NULL,

    -- Timestamp (UTC)
    sent_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_streak_reminders_user_profile ON streak_reminders(user_id, profile_id);
CREATE INDEX idx_streak_reminders_sent_date ON streak_reminders(sent_date);

-- Уникальность: одно напоминание в день на профиль
CREATE UNIQUE INDEX idx_streak_reminders_unique_per_day ON streak_reminders(user_id, profile_id, sent_date);
```

**Примечания:**
- Используется для предотвращения дублирующих напоминаний
- `sent_date` - дата по местному времени пользователя
- `sent_at` - UTC время отправки
- Записи старше 7 дней можно удалять

---

### Таблица: activity_log

**Описание:** Лог активности пользователей (для статистики)

```sql
CREATE TABLE activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    profile_id UUID REFERENCES language_profiles(id) ON DELETE SET NULL,

    -- Activity
    action_type VARCHAR(50) NOT NULL,  -- card_added, card_studied, exercise_completed, message_sent, etc.
    action_date DATE NOT NULL,

    -- Time
    time_minutes INT NOT NULL DEFAULT 0,

    -- Metadata
    metadata JSONB,

    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_activity_log_user_date ON activity_log(user_id, action_date);
CREATE INDEX idx_activity_log_profile_date ON activity_log(profile_id, action_date);
CREATE INDEX idx_activity_log_action_type ON activity_log(action_type);

-- Партиционирование по месяцам (для производительности)
-- ALTER TABLE activity_log PARTITION BY RANGE (action_date);
```

**Примечания:**
- Используется для календаря активности и статистики
- `action_type` - тип действия
- `time_minutes` - время активности в минутах
- Можно партиционировать по месяцам для производительности

---

### Таблица: token_usage

**Описание:** Использование токенов LLM (для мониторинга и лимитов)

```sql
CREATE TABLE token_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    profile_id UUID REFERENCES language_profiles(id) ON DELETE SET NULL,

    -- Tokens
    prompt_tokens INT NOT NULL,
    completion_tokens INT NOT NULL,
    total_tokens INT NOT NULL,

    -- Cost
    estimated_cost DECIMAL(10, 6) NOT NULL,

    -- Model
    model VARCHAR(50) NOT NULL DEFAULT 'gpt-4-1106-preview',

    -- Timestamp
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_token_usage_user_id ON token_usage(user_id);
CREATE INDEX idx_token_usage_timestamp ON token_usage(timestamp);

-- Партиционирование по месяцам
-- ALTER TABLE token_usage PARTITION BY RANGE (timestamp);
```

**Примечания:**
- Отслеживаем расход токенов для каждого запроса
- `estimated_cost` - примерная стоимость в долларах
- Используется для аналитики и оптимизации
- Можно партиционировать по времени

---

## Индексы

### Основные индексы (уже включены в схему)

**Performance-critical индексы:**
1. `idx_users_telegram_id` - UNIQUE index на telegram_id (аутентификация)
2. `idx_profiles_user_active` - составной index для поиска активного профиля
3. `idx_cards_next_review` - для выборки карточек к повторению
4. `idx_cards_deck_lemma` - UNIQUE index для проверки дубликатов
5. `idx_conversation_user_profile` - для получения истории диалога
6. `idx_exercise_history_completed_at` - для сортировки истории

### Дополнительные индексы для аналитики

```sql
-- Поиск групп пользователя
CREATE INDEX idx_group_members_user_groups ON group_members(user_id, group_id);

-- Статистика по датам
CREATE INDEX idx_card_reviews_date ON card_reviews(DATE(reviewed_at));
CREATE INDEX idx_exercise_history_date ON exercise_history(DATE(completed_at));

-- Поиск материалов группы
CREATE INDEX idx_group_materials_group_type ON group_materials(group_id, material_type);
```

### Мониторинг индексов

```sql
-- Проверка использования индексов
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;

-- Неиспользуемые индексы (кандидаты на удаление)
SELECT
    schemaname,
    tablename,
    indexname
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexname NOT LIKE 'pg_toast%';
```

---

## Триггеры и функции

### 1. Автоматическое обновление updated_at

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Применяется ко всем таблицам с updated_at через:
-- CREATE TRIGGER update_{table}_updated_at BEFORE UPDATE ON {table}
--     FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 2. Обновление счетчиков в decks

```sql
-- Обновление cards_count при добавлении/удалении карточки
CREATE OR REPLACE FUNCTION update_deck_cards_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE decks SET cards_count = cards_count + 1 WHERE id = NEW.deck_id;
        IF NEW.status = 'new' THEN
            UPDATE decks SET new_cards_count = new_cards_count + 1 WHERE id = NEW.deck_id;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE decks SET cards_count = cards_count - 1 WHERE id = OLD.deck_id;
        IF OLD.status = 'new' THEN
            UPDATE decks SET new_cards_count = new_cards_count - 1 WHERE id = OLD.deck_id;
        END IF;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.status = 'new' AND NEW.status != 'new' THEN
            UPDATE decks SET new_cards_count = new_cards_count - 1 WHERE id = NEW.deck_id;
        ELSIF OLD.status != 'new' AND NEW.status = 'new' THEN
            UPDATE decks SET new_cards_count = new_cards_count + 1 WHERE id = NEW.deck_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_deck_cards_count_trigger
AFTER INSERT OR UPDATE OR DELETE ON cards
FOR EACH ROW EXECUTE FUNCTION update_deck_cards_count();
```

### 3. Обновление счетчиков в topics

```sql
CREATE OR REPLACE FUNCTION update_topic_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE topics SET
        exercises_count = exercises_count + 1,
        correct_count = correct_count + CASE WHEN NEW.result = 'correct' THEN 1 ELSE 0 END,
        partial_count = partial_count + CASE WHEN NEW.result = 'partial' THEN 1 ELSE 0 END,
        incorrect_count = incorrect_count + CASE WHEN NEW.result = 'incorrect' THEN 1 ELSE 0 END,
        accuracy = (
            (correct_count + CASE WHEN NEW.result = 'correct' THEN 1 ELSE 0 END)::DECIMAL /
            (exercises_count + 1)
        )
    WHERE id = NEW.topic_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_topic_stats_trigger
AFTER INSERT ON exercise_history
FOR EACH ROW EXECUTE FUNCTION update_topic_stats();
```

### 4. Автоматическое истечение приглашений

```sql
-- Функция для периодического запуска (через cron)
CREATE OR REPLACE FUNCTION expire_old_invites()
RETURNS void AS $$
BEGIN
    UPDATE group_invites
    SET status = 'expired'
    WHERE status = 'pending'
      AND expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Запускать через pg_cron:
-- SELECT cron.schedule('expire-invites', '0 * * * *', 'SELECT expire_old_invites()');
```

---

## Миграции

### Инструмент: Alembic

**Установка:**
```bash
pip install alembic
alembic init migrations
```

**Конфигурация (alembic.ini):**
```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql://user:password@localhost/langbot

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic
```

**Структура:**
```
migrations/
├── versions/
│   ├── 001_initial_schema.py
│   ├── 002_add_streak_reminders.py
│   └── 003_add_activity_log.py
├── env.py
└── script.py.mako
```

### Создание миграции

```bash
# Автогенерация на основе моделей SQLAlchemy
alembic revision --autogenerate -m "Add streak reminders table"

# Ручная миграция
alembic revision -m "Add index on cards.next_review"
```

### Применение миграций

```bash
# Development
alembic upgrade head

# Production (с подтверждением)
alembic upgrade head --sql > migration.sql
# Проверяем migration.sql
psql -U user -d langbot < migration.sql

# Rollback
alembic downgrade -1
```

### Пример миграции

```python
# migrations/versions/001_initial_schema.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('first_name', sa.String(255), nullable=False),
        sa.Column('last_name', sa.String(255)),
        sa.Column('username', sa.String(255)),
        sa.Column('is_premium', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )

    op.create_index('idx_users_telegram_id', 'users', ['telegram_id'], unique=True)

    # ... остальные таблицы

def downgrade():
    op.drop_table('users')
```

### Стратегия миграций

**Development:**
- Свободно создаем и откатываем миграции
- Можем удалять и пересоздавать миграции

**Production:**
1. **Тестируем миграцию на копии production БД**
2. **Создаем backup перед миграцией**
3. **Применяем в окне обслуживания (если требуется downtime)**
4. **Мониторим производительность после миграции**

**Zero-downtime миграции:**
- Добавление колонок: OK
- Удаление колонок: требует 2 этапа (сначала код, потом БД)
- Изменение типов: требует временную колонку
- Добавление индексов: CONCURRENTLY

```sql
-- Добавление индекса без блокировки таблицы
CREATE INDEX CONCURRENTLY idx_new_index ON table_name(column_name);
```

---

## Backup и восстановление

### Стратегия резервного копирования

**1. Automated Daily Backups**

**Полный backup (ежедневно в 3:00 UTC):**
```bash
#!/bin/bash
# /scripts/backup.sh

DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR=/backups/postgresql
DATABASE=langbot

# Full backup
pg_dump -U postgres -F c -b -v -f "$BACKUP_DIR/langbot_$DATE.backup" $DATABASE

# Сжатие
gzip "$BACKUP_DIR/langbot_$DATE.backup"

# Удаление бэкапов старше 30 дней
find $BACKUP_DIR -name "*.backup.gz" -mtime +30 -delete

# Копирование архива во внешнее объектное хранилище (пример с rclone)
rclone copy "$BACKUP_DIR/langbot_$DATE.backup.gz" object-storage:langbot/backups/
```

**Cron:**
```cron
0 3 * * * /scripts/backup.sh >> /var/log/backup.log 2>&1
```

**2. Point-in-Time Recovery (PITR)**

**Настройка WAL archiving:**
```conf
# postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /mnt/archive/%f && cp %p /mnt/archive/%f'
archive_timeout = 300  # 5 минут
```

**Преимущества:**
- Восстановление на любую секунду
- Минимальная потеря данных (RPO < 5 минут)

**3. Streaming Replication (для Production)**

**Настройка standby сервера:**
```conf
# primary
max_wal_senders = 3
wal_keep_size = 1GB

# standby
primary_conninfo = 'host=primary-db port=5432 user=replicator password=secret'
restore_command = 'cp /mnt/archive/%f %p'
```

### Восстановление

**Из полного backup:**
```bash
# 1. Остановить приложение
systemctl stop langbot-backend

# 2. Создать новую БД (если нужно)
createdb langbot_restore

# 3. Восстановить из backup
gunzip -c /backups/langbot_2025-01-08.backup.gz | pg_restore -U postgres -d langbot_restore -v

# 4. Проверить данные
psql -U postgres langbot_restore

# 5. Переключить приложение на новую БД
# Изменить DATABASE_URL в .env

# 6. Запустить приложение
systemctl start langbot-backend
```

**Point-in-Time Recovery:**
```bash
# 1. Восстановить последний полный backup
pg_restore -d langbot_restore /backups/langbot_2025-01-08.backup

# 2. Применить WAL до нужного времени
# recovery.conf
restore_command = 'cp /mnt/archive/%f %p'
recovery_target_time = '2025-01-08 14:30:00'

# 3. Запустить PostgreSQL (автоматически применит WAL)
```

### Тестирование backup

**Регулярно (раз в месяц):**
```bash
# 1. Восстановить backup в тестовую БД
pg_restore -d test_restore /backups/latest.backup

# 2. Проверить целостность
psql -d test_restore -c "SELECT COUNT(*) FROM users;"
psql -d test_restore -c "SELECT COUNT(*) FROM cards;"

# 3. Запустить тесты приложения на тестовой БД
pytest --database-url=postgresql://localhost/test_restore

# 4. Удалить тестовую БД
dropdb test_restore
```

### Мониторинг backups

**Проверка успешности:**
```bash
# Последний успешный backup
ls -lh /backups/postgresql/ | tail -1

# Размер backups
du -sh /backups/postgresql/

# Alert если backup не создался в последние 25 часов
find /backups/postgresql/ -name "*.backup.gz" -mtime -1 | grep -q . || \
  echo "ALERT: No recent backups found!"
```

### Шифрование backups

```bash
# Шифрование backup перед загрузкой в облако
pg_dump -U postgres -F c langbot | \
  gzip | \
  openssl enc -aes-256-cbc -salt -pass pass:$BACKUP_PASSWORD > \
  /backups/langbot_encrypted_$DATE.backup.gz.enc

# Расшифровка
openssl enc -aes-256-cbc -d -pass pass:$BACKUP_PASSWORD \
  -in /backups/langbot_encrypted_$DATE.backup.gz.enc | \
  gunzip | \
  pg_restore -U postgres -d langbot_restore
```

### Retention Policy

**Хранение backups:**
- Ежедневные: 30 дней
- Еженедельные (воскресенье): 3 месяца
- Ежемесячные (1-е число): 1 год

```bash
# Скрипт для применения retention policy
#!/bin/bash

BACKUP_DIR=/backups/postgresql

# Ежедневные (старше 30 дней)
find $BACKUP_DIR/daily -name "*.backup.gz" -mtime +30 -delete

# Еженедельные (старше 90 дней)
find $BACKUP_DIR/weekly -name "*.backup.gz" -mtime +90 -delete

# Ежемесячные (старше 365 дней)
find $BACKUP_DIR/monthly -name "*.backup.gz" -mtime +365 -delete
```

---

## Мониторинг производительности

### Key Metrics

**1. Размер БД:**
```sql
SELECT
    pg_size_pretty(pg_database_size('langbot')) as database_size;
```

**2. Размер таблиц:**
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**3. Медленные запросы:**
```sql
-- Включить логирование медленных запросов
-- postgresql.conf
log_min_duration_statement = 1000  -- 1 секунда

-- Топ медленных запросов
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**4. Статистика таблиц:**
```sql
SELECT
    schemaname,
    tablename,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;
```

### Оптимизация

**VACUUM и ANALYZE:**
```sql
-- Регулярно (автоматически через autovacuum)
VACUUM ANALYZE;

-- Для конкретных таблиц
VACUUM ANALYZE cards;
VACUUM ANALYZE conversation_history;
```

**Настройка autovacuum:**
```conf
# postgresql.conf
autovacuum = on
autovacuum_naptime = 1min
autovacuum_vacuum_threshold = 50
autovacuum_analyze_threshold = 50
```

---

Этот документ описывает полную схему базы данных PostgreSQL для Telegram-бота изучения языков с ИИ-преподавателем, включая все таблицы, индексы, триггеры, миграции и стратегию резервного копирования.
