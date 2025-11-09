# Монетизация и подписки

## Общая концепция

Система подписок построена на модели freemium с двумя тарифами:
- **Бесплатный план** - базовая функциональность с ограничениями
- **Премиум план** - расширенная функциональность без ограничений

Все новые пользователи получают **7-дневный пробный период** с доступом к премиум-функциям без привязки карты.

---

## Модель подписки

### Бесплатный тариф (Free Tier)

**Ограничения:**

| Ресурс | Лимит |
|--------|-------|
| Языковые профили | 1 профиль |
| LLM сообщения | 50 сообщений/день |
| Упражнения | 10 упражнений/день |
| Карточки | 200 карточек максимум |
| Группы | 1 группа (по 5 участников) |

**Что доступно:**
- Полный диалог с ИИ-преподавателем (в рамках лимитов)
- Создание и изучение карточек
- Выполнение упражнений
- Участие в группах без ограничений
- Базовая статистика и стрики
- Работа с изображениями (OCR)
- Голосовые сообщения

**Что недоступно:**
- Создание дополнительных языковых профилей
- Неограниченное общение с ботом
- Неограниченное количество карточек
- Создание нескольких групп
- Расширенные лимиты участников в группах

### Премиум подписка (Premium Tier)

**Расширенные лимиты:**

| Ресурс | Лимит |
|--------|-------|
| Языковые профили | Без ограничений (практически до 10) |
| LLM сообщения | 500 сообщений/день |
| Упражнения | Без ограничений |
| Карточки | Без ограничений |
| Группы | Без ограничений (по 100 участников) |

**Дополнительные возможности:**
- Изучение нескольких языков одновременно (до 10 профилей)
- Приоритетная поддержка
- Ранний доступ к новым функциям
- Создание групп без ограничений
- До 100 участников в каждой группе (vs 5 для free)

**Тарифные планы:**

```
Месячная подписка: €4.99/месяц
Годовая подписка:  €49/год (экономия ~17%, €4.08/месяц)
```

**Автопродление:**
- По умолчанию включено через Stripe
- Можно отключить в любой момент через настройки или панель Stripe
- При отключении подписка действует до конца оплаченного периода

---

## Функции премиума

### Увеличенные лимиты

#### LLM сообщения
- **Free:** 50 сообщений/день
- **Premium:** 500 сообщений/день
- **Применяется к:**
  - Диалогам с ботом
  - Генерации карточек через LLM
  - Генерации упражнений
  - Проверке ответов
  - OCR с изображениями

#### Карточки
- **Free:** максимум 200 карточек
- **Premium:** без ограничений
- **При превышении лимита (free):**
  - Доступ к существующим карточкам только для чтения
  - Нельзя добавлять новые
  - Можно продолжать изучать существующие

#### Языковые профили
- **Free:** 1 профиль (один язык)
- **Premium:** до 10 профилей (несколько языков одновременно)
- **При переходе с premium на free:**
  - Все профили сохраняются
  - Можно переключаться между ними
  - Нельзя создавать новые до удаления лишних

#### Группы и коллаборация
- **Free:**
  - 1 группа-владелец
  - 5 участников на группу
  - Неограниченное участие в группах других пользователей
- **Premium:**
  - Неограниченное количество групп-владельцев
  - 100 участников на группу
  - Неограниченное участие в группах

#### Упражнения
- **Free:** 10 упражнений/день
- **Premium:** без ограничений
- Учитываются в общем лимите LLM сообщений

### Дополнительные возможности

#### Приоритетная поддержка
- Приоритетная обработка запросов в техподдержку
- Прямой канал связи с командой разработки
- Более быстрое время отклика на баги и предложения

#### Ранний доступ
- Beta-тестирование новых функций
- Влияние на развитие продукта через опросы
- Эксклюзивный доступ к экспериментальным возможностям

#### Будущие функции (в планах для v2.0)
- Персонализированные рекомендации тем на основе AI-анализа
- Экспорт прогресса в различных форматах
- Интеграция с внешними сервисами (Anki, Quizlet)
- Офлайн-режим в Mini App

### Аналитика и статистика

**Базовая статистика (Free + Premium):**
- Текущий стрик
- Количество карточек/упражнений
- Календарь активности
- Процент правильных ответов по темам

**Расширенные метрики (Premium, планируется для v2.0):**
- Детальная аналитика времени обучения
- Прогнозы достижения целевого уровня
- Сравнение с другими пользователями (анонимно)
- Рекомендации по оптимизации обучения
- Экспорт статистики в CSV/JSON

---

## Пробный период (Trial)

### Параметры триала

**Длительность:** 7 дней

**Доступ:**
- Полный премиум-функционал
- Все лимиты премиум-плана

**Условия:**
- Не требуется привязка карты
- Автоматически активируется при регистрации
- Доступен один раз на пользователя
- Нельзя повторно активировать

**Окончание триала:**
- Автоматический переход на бесплатный план
- Все данные сохраняются
- Применяются ограничения free tier
- Уведомление за 1 день до окончания

### Отслеживание триала

**Поля в БД:**

```sql
-- users table
trial_ends_at TIMESTAMP          -- Дата окончания триала
trial_used BOOLEAN DEFAULT FALSE -- Уже использовал триал
```

**Логика:**

```python
def check_trial_status(user: User) -> dict:
    """
    Проверяет статус триала пользователя.
    """
    now = datetime.utcnow()

    # Триал активен
    if user.trial_ends_at and user.trial_ends_at > now:
        return {
            'status': 'trial',
            'active': True,
            'expires_at': user.trial_ends_at,
            'days_remaining': (user.trial_ends_at - now).days
        }

    # Триал истек
    if user.trial_used:
        return {
            'status': 'trial',
            'active': False,
            'expired': True
        }

    # Триал не использовался (не должно быть)
    return {
        'status': 'trial',
        'active': False,
        'available': True
    }
```

---

## Активация подписки

### Автоматическая активация через Stripe

#### Интеграция с платежной системой

**Платежный провайдер:** Stripe

**Преимущества:**
- Поддержка международных карт
- PCI DSS compliance из коробки
- Webhooks для автоматизации
- Готовые UI компоненты (Stripe Checkout)
- Управление подписками и recurring payments
- Автоматическая обработка failed payments

#### Процесс оплаты

**1. Создание Checkout Session**

```python
@app.post('/api/subscriptions/create-checkout')
def create_checkout_session(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Создает Stripe Checkout Session для оформления подписки.
    """
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Определяем Price ID в зависимости от плана
    price_id = {
        'monthly': settings.STRIPE_PRICE_MONTHLY,
        'yearly': settings.STRIPE_PRICE_YEARLY
    }[request.plan]

    # Создаем или получаем Stripe Customer
    if not current_user.subscription or not current_user.subscription.stripe_customer_id:
        customer = stripe.Customer.create(
            email=current_user.email if current_user.email else None,
            metadata={
                'user_id': str(current_user.id),
                'telegram_id': current_user.telegram_id
            }
        )
        customer_id = customer.id
    else:
        customer_id = current_user.subscription.stripe_customer_id

    # Создаем Checkout Session
    checkout_session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=['card'],
        line_items=[{
            'price': price_id,
            'quantity': 1,
        }],
        mode='subscription',
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        metadata={
            'user_id': str(current_user.id)
        }
    )

    return {
        'checkout_session_id': checkout_session.id,
        'checkout_url': checkout_session.url
    }
```

**Request:**
```json
{
  "plan": "yearly",
  "success_url": "https://t.me/bot?start=payment_success",
  "cancel_url": "https://t.me/bot?start=payment_cancel"
}
```

**Response:**
```json
{
  "checkout_session_id": "cs_xxx",
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_xxx"
}
```

**2. Пользователь оплачивает**

- Frontend открывает `checkout_url`
- Пользователь вводит данные карты
- Stripe обрабатывает платеж
- Redirect на `success_url` или `cancel_url`

**3. Stripe отправляет Webhook**

Stripe отправляет событие `checkout.session.completed` на наш webhook endpoint.

#### Обработка Webhooks

**Endpoint:**

```python
@app.post('/api/subscriptions/webhook')
async def stripe_webhook(request: Request):
    """
    Обрабатывает webhooks от Stripe.
    ВАЖНО: Должен быть доступен по HTTPS для production!
    """
    import stripe

    payload = await request.body()
    sig_header = request.headers.get('Stripe-Signature')

    try:
        # Верифицируем подпись
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Обрабатываем события
    event_type = event['type']
    event_data = event['data']['object']

    if event_type == 'checkout.session.completed':
        handle_checkout_completed(event_data)

    elif event_type == 'invoice.paid':
        handle_invoice_paid(event_data)

    elif event_type == 'invoice.payment_failed':
        handle_payment_failed(event_data)

    elif event_type == 'customer.subscription.updated':
        handle_subscription_updated(event_data)

    elif event_type == 'customer.subscription.deleted':
        handle_subscription_deleted(event_data)

    return {'received': True}
```

**Обработчики событий:**

```python
def handle_checkout_completed(session: dict):
    """
    Активирует подписку после успешной оплаты.
    """
    user_id = session['metadata']['user_id']
    customer_id = session['customer']
    subscription_id = session['subscription']

    # Получаем детали подписки из Stripe
    import stripe
    subscription = stripe.Subscription.retrieve(subscription_id)

    # Создаем или обновляем подписку в БД
    user = db.query(User).filter(User.id == user_id).first()

    if not user.subscription:
        user.subscription = Subscription(user_id=user_id)

    user.subscription.stripe_customer_id = customer_id
    user.subscription.stripe_subscription_id = subscription_id
    user.subscription.status = 'active'
    user.subscription.plan = 'monthly' if subscription.items.data[0].price.recurring.interval == 'month' else 'yearly'
    user.subscription.price = subscription.items.data[0].price.unit_amount / 100  # Cents to euros
    user.subscription.currency = subscription.items.data[0].price.currency.upper()
    user.subscription.current_period_start = datetime.fromtimestamp(subscription.current_period_start)
    user.subscription.current_period_end = datetime.fromtimestamp(subscription.current_period_end)

    # Активируем премиум на пользователе
    user.is_premium = True
    user.premium_expires_at = user.subscription.current_period_end

    db.commit()

    # Отправляем уведомление пользователю
    send_notification(user, 'subscription_activated')

    logger.info(f"Subscription activated: user_id={user_id}, subscription_id={subscription_id}")


def handle_subscription_updated(subscription: dict):
    """
    Обновляет данные подписки при изменениях.
    """
    subscription_id = subscription['id']

    db_subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()

    if not db_subscription:
        logger.warning(f"Subscription not found: {subscription_id}")
        return

    # Обновляем статус
    db_subscription.status = subscription['status']  # active, canceled, past_due, etc.
    db_subscription.cancel_at_period_end = subscription['cancel_at_period_end']
    db_subscription.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])

    # Если подписка отменена
    if subscription['cancel_at_period_end']:
        db_subscription.canceled_at = datetime.fromtimestamp(subscription['canceled_at'])

    db.commit()

    logger.info(f"Subscription updated: {subscription_id}, status={subscription['status']}")


def handle_subscription_deleted(subscription: dict):
    """
    Обрабатывает удаление/истечение подписки.
    """
    subscription_id = subscription['id']

    db_subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()

    if not db_subscription:
        return

    # Меняем статус
    db_subscription.status = 'expired'

    # Деактивируем премиум
    user = db_subscription.user
    user.is_premium = False
    user.premium_expires_at = None

    db.commit()

    # Уведомляем пользователя
    send_notification(user, 'subscription_expired')

    logger.info(f"Subscription deleted: user_id={user.id}")
```

**События Stripe:**

| Событие | Когда происходит | Действие |
|---------|------------------|----------|
| `checkout.session.completed` | Успешная оплата через Checkout | Активируем подписку |
| `invoice.paid` | Успешное списание (renewal) | Продлеваем подписку |
| `invoice.payment_failed` | Неудачная оплата | Уведомляем пользователя, переводим в past_due |
| `customer.subscription.updated` | Изменение подписки | Обновляем данные в БД |
| `customer.subscription.deleted` | Удаление подписки | Деактивируем премиум |

#### Управление подпиской пользователем

**Отмена подписки:**

```python
@app.post('/api/subscriptions/cancel')
def cancel_subscription(current_user: User = Depends(get_current_user)):
    """
    Отменяет подписку (автопродление).
    Подписка действует до конца оплаченного периода.
    """
    if not current_user.subscription or current_user.subscription.status != 'active':
        raise HTTPException(status_code=400, detail="No active subscription")

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Отменяем в Stripe
    subscription = stripe.Subscription.modify(
        current_user.subscription.stripe_subscription_id,
        cancel_at_period_end=True
    )

    # Обновляем в БД
    current_user.subscription.cancel_at_period_end = True
    current_user.subscription.canceled_at = datetime.utcnow()
    db.commit()

    return {
        'status': 'active',
        'cancel_at_period_end': True,
        'current_period_end': current_user.subscription.current_period_end,
        'message': f"Подписка будет отменена {current_user.subscription.current_period_end.strftime('%d.%m.%Y')}"
    }
```

**Возобновление подписки:**

```python
@app.post('/api/subscriptions/reactivate')
def reactivate_subscription(current_user: User = Depends(get_current_user)):
    """
    Возобновляет подписку (отменяет cancel_at_period_end).
    """
    if not current_user.subscription or not current_user.subscription.cancel_at_period_end:
        raise HTTPException(status_code=400, detail="Subscription not canceled")

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Возобновляем в Stripe
    subscription = stripe.Subscription.modify(
        current_user.subscription.stripe_subscription_id,
        cancel_at_period_end=False
    )

    # Обновляем в БД
    current_user.subscription.cancel_at_period_end = False
    current_user.subscription.canceled_at = None
    db.commit()

    return {
        'status': 'active',
        'cancel_at_period_end': False,
        'message': 'Подписка возобновлена'
    }
```

### Ручная активация администратором

Используется для:
- Промо-акций
- Компенсаций за баги
- Специальных предложений
- Тестирования

**Endpoint:**

```python
@app.post('/api/admin/users/{user_id}/premium')
def manually_activate_premium(
    user_id: UUID,
    request: ManualPremiumRequest,
    current_admin: User = Depends(require_admin)
):
    """
    Вручную активирует премиум для пользователя.
    Только для администраторов.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Активируем премиум
    user.is_premium = True

    if request.duration_days == "unlimited":
        user.premium_expires_at = None  # Бессрочно
    else:
        user.premium_expires_at = datetime.utcnow() + timedelta(days=request.duration_days)

    # Создаем или обновляем запись подписки
    if not user.subscription:
        user.subscription = Subscription(user_id=user_id)

    user.subscription.status = 'active'
    user.subscription.plan = None  # Ручная активация

    db.commit()

    # Логируем действие администратора
    log_admin_action(
        admin_id=current_admin.id,
        action='manual_premium_activation',
        target_user_id=user_id,
        details={
            'duration_days': request.duration_days,
            'reason': request.reason
        }
    )

    # Уведомляем пользователя
    send_notification(user, 'premium_activated_manually', {
        'duration': request.duration_days,
        'reason': request.reason
    })

    return {
        'user_id': str(user_id),
        'is_premium': True,
        'expires_at': user.premium_expires_at.isoformat() if user.premium_expires_at else None,
        'reason': request.reason
    }
```

**Request:**
```json
{
  "duration_days": 30,
  "reason": "Compensation for bug #145"
}
```

или

```json
{
  "duration_days": "unlimited",
  "reason": "Team member"
}
```

**Логирование:**

Все действия администраторов логируются для аудита:

```python
class AdminActionLog(Base):
    __tablename__ = 'admin_action_logs'

    id = Column(UUID, primary_key=True, default=uuid4)
    admin_id = Column(UUID, ForeignKey('users.id'), nullable=False)
    action = Column(String, nullable=False)  # 'manual_premium_activation', etc.
    target_user_id = Column(UUID, ForeignKey('users.id'))
    details = Column(JSONB)  # Дополнительные данные
    timestamp = Column(DateTime, default=datetime.utcnow)
```

---

## Проверка статуса подписки

### Получение лимитов пользователя

**Функция для вычисления лимитов:**

```python
def get_user_limits(user: User) -> dict:
    """
    Возвращает текущие лимиты пользователя на основе статуса подписки.
    """
    # Проверяем статус премиум
    is_premium = user.is_premium

    # Проверяем триал
    if user.trial_ends_at and user.trial_ends_at > datetime.utcnow():
        is_premium = True

    # Базовые лимиты
    if is_premium:
        limits = {
            'profiles': {'max': 10},
            'messages': {'max': 500, 'reset_interval': 'daily'},
            'exercises': {'max': None},  # Unlimited
            'cards': {'max': None},      # Unlimited
            'groups': {'max': None, 'members_per_group': 100}
        }
    else:
        limits = {
            'profiles': {'max': 1},
            'messages': {'max': 50, 'reset_interval': 'daily'},
            'exercises': {'max': 10, 'reset_interval': 'daily'},
            'cards': {'max': 200},
            'groups': {'max': 1, 'members_per_group': 5}
        }

    # Добавляем текущее использование
    limits['profiles']['used'] = db.query(LanguageProfile).filter(
        LanguageProfile.user_id == user.id,
        LanguageProfile.deleted == False
    ).count()

    limits['cards']['used'] = db.query(Card).join(Deck).filter(
        Deck.user_id == user.id,
        Card.deleted == False
    ).count()

    # Дневные лимиты (из Redis)
    limits['messages']['used'] = get_daily_usage(user.id, 'messages')
    limits['messages']['reset_at'] = get_next_reset_time()

    if limits['exercises']['max'] is not None:
        limits['exercises']['used'] = get_daily_usage(user.id, 'exercises')
        limits['exercises']['reset_at'] = get_next_reset_time()

    limits['groups']['used'] = db.query(Group).filter(
        Group.owner_id == user.id,
        Group.deleted == False
    ).count()

    return limits


def get_daily_usage(user_id: UUID, resource_type: str) -> int:
    """
    Получает дневное использование из Redis.
    """
    key = f"daily_usage:{resource_type}:{user_id}:{datetime.utcnow().date()}"
    usage = redis_client.get(key)
    return int(usage) if usage else 0


def increment_daily_usage(user_id: UUID, resource_type: str):
    """
    Инкрементирует дневной счетчик использования.
    """
    key = f"daily_usage:{resource_type}:{user_id}:{datetime.utcnow().date()}"

    if not redis_client.exists(key):
        # Устанавливаем TTL до конца дня
        midnight = datetime.combine(datetime.utcnow().date() + timedelta(days=1), datetime.min.time())
        ttl = int((midnight - datetime.utcnow()).total_seconds())
        redis_client.setex(key, ttl, 1)
    else:
        redis_client.incr(key)


def get_next_reset_time() -> str:
    """
    Возвращает время следующего сброса (полночь UTC).
    """
    tomorrow = datetime.utcnow().date() + timedelta(days=1)
    midnight = datetime.combine(tomorrow, datetime.min.time())
    return midnight.isoformat()
```

### Middleware для проверки лимитов

**Декоратор для проверки:**

```python
def require_limit(resource_type: str):
    """
    Декоратор для проверки лимитов перед выполнением действия.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User, **kwargs):
            limits = get_user_limits(current_user)

            # Проверяем лимит
            resource_limits = limits.get(resource_type)
            if not resource_limits:
                return await func(*args, current_user=current_user, **kwargs)

            max_limit = resource_limits.get('max')
            current_usage = resource_limits.get('used', 0)

            # Unlimited
            if max_limit is None:
                return await func(*args, current_user=current_user, **kwargs)

            # Проверяем превышение
            if current_usage >= max_limit:
                raise HTTPException(
                    status_code=400 if current_user.is_premium else 402,
                    detail={
                        'code': 'LIMIT_REACHED',
                        'message': f"Достигнут лимит {resource_type} ({max_limit})",
                        'details': {
                            'limit_type': resource_type,
                            'current': current_usage,
                            'max': max_limit,
                            'reset_at': resource_limits.get('reset_at'),
                            'upgrade_url': '/profile/premium' if not current_user.is_premium else None
                        }
                    }
                )

            # Выполняем функцию
            result = await func(*args, current_user=current_user, **kwargs)

            # Инкрементируем счетчик (если это дневной лимит)
            if resource_limits.get('reset_interval') == 'daily':
                increment_daily_usage(current_user.id, resource_type)

            return result

        return wrapper
    return decorator
```

**Использование:**

```python
@app.post('/api/cards')
@require_limit('cards')
async def create_card(
    request: CreateCardRequest,
    current_user: User = Depends(get_current_user)
):
    # Лимит уже проверен декоратором
    card = await create_card_for_user(current_user, request)
    return serialize_card(card)


@app.post('/api/exercises/generate')
@require_limit('exercises')
async def generate_exercise(
    request: GenerateExerciseRequest,
    current_user: User = Depends(get_current_user)
):
    # Лимит проверен, инкрементирован
    exercise = await llm_generate_exercise(current_user, request)
    return exercise
```

### Уведомления пользователю о лимитах

#### При достижении лимита

**Формат ответа:**

```json
{
  "error": {
    "code": "LIMIT_REACHED",
    "message": "Достигнут дневной лимит сообщений (50)",
    "details": {
      "limit_type": "messages",
      "current": 50,
      "max": 50,
      "reset_at": "2025-01-09T00:00:00Z",
      "upgrade_url": "/profile/premium"
    }
  }
}
```

**В боте:**

```
❌ Достигнут дневной лимит сообщений (50)

Ваши лимиты будут сброшены через 3 часа (в 00:00 UTC).

💎 С Премиум подпиской вы получите:
• 500 сообщений в день (вместо 50)
• Неограниченные упражнения
• Неограниченные карточки
• До 10 языковых профилей

[Оформить Премиум →]
```

#### Предупреждение перед достижением

При приближении к лимиту (80%) показываем предупреждение:

```python
def check_limit_warning(user: User, resource_type: str):
    """
    Проверяет, нужно ли показать предупреждение о лимите.
    """
    limits = get_user_limits(user)
    resource = limits.get(resource_type, {})

    max_limit = resource.get('max')
    current = resource.get('used', 0)

    if max_limit is None:  # Unlimited
        return None

    threshold = max_limit * 0.8

    if current >= threshold and current < max_limit:
        return {
            'warning': True,
            'message': f"Вы использовали {current} из {max_limit} {resource_type}",
            'remaining': max_limit - current,
            'reset_at': resource.get('reset_at')
        }

    return None
```

**В ответах API:**

```json
{
  "data": { ... },
  "limit_warning": {
    "warning": true,
    "message": "Вы использовали 45 из 50 сообщений",
    "remaining": 5,
    "reset_at": "2025-01-09T00:00:00Z"
  }
}
```

#### Статус лимитов в профиле

**GET /api/users/me включает лимиты:**

```json
{
  "id": "uuid",
  "telegram_id": 123456789,
  "is_premium": false,
  "limits": {
    "profiles": { "used": 1, "max": 1 },
    "messages": { "used": 45, "max": 50, "reset_at": "2025-01-09T00:00:00Z" },
    "exercises": { "used": 8, "max": 10, "reset_at": "2025-01-09T00:00:00Z" },
    "cards": { "used": 124, "max": 200 },
    "groups": { "used": 0, "max": 1 }
  }
}
```

**В Mini App:**

Отображаются прогресс-бары для каждого лимита:

```
📊 Ваши лимиты

Сообщения:  [████████░░] 45/50
Упражнения: [████████░░] 8/10
Карточки:   [██████░░░░] 124/200
Профили:    [██████████] 1/1

Сброс лимитов через: 3 часа

[💎 Оформить Премиум]
```

---

## Управление подписками

### База данных подписок

**Таблица subscriptions:**

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

-- Trigger для updated_at
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Статусы подписки:**

| Статус | Описание |
|--------|----------|
| `free` | Бесплатный план (подписка не оформлена) |
| `trial` | Пробный период (7 дней) |
| `active` | Активная оплаченная подписка |
| `canceled` | Отменена (действует до конца периода) |
| `expired` | Истекла |

**Связь с таблицей users:**

```sql
-- users table
is_premium BOOLEAN NOT NULL DEFAULT FALSE
premium_expires_at TIMESTAMP
trial_ends_at TIMESTAMP
trial_used BOOLEAN NOT NULL DEFAULT FALSE
```

- `is_premium` - кэшированный статус для быстрой проверки
- `premium_expires_at` - дата истечения премиума (из subscription)
- `trial_ends_at` - дата окончания триала
- `trial_used` - флаг использованного триала

### Истечение подписки

**Автоматическая проверка:**

Запускается через cron job каждые 15 минут:

```python
def check_expired_subscriptions():
    """
    Проверяет истекшие подписки и деактивирует премиум.
    """
    now = datetime.utcnow()

    # Находим истекшие подписки
    expired_subscriptions = db.query(Subscription).filter(
        Subscription.status == 'active',
        Subscription.current_period_end <= now
    ).all()

    for subscription in expired_subscriptions:
        user = subscription.user

        # Деактивируем премиум
        user.is_premium = False
        user.premium_expires_at = None
        subscription.status = 'expired'

        db.commit()

        # Отправляем уведомление
        send_notification(user, 'subscription_expired')

        logger.info(f"Subscription expired: user_id={user.id}")
```

**Cron задача:**

```bash
# crontab -e
*/15 * * * * python /app/scripts/check_expired_subscriptions.py
```

**Или через pg_cron (если используется PostgreSQL):**

```sql
SELECT cron.schedule(
    'check-expired-subscriptions',
    '*/15 * * * *',
    $$SELECT check_expired_subscriptions()$$
);
```

**Что происходит при истечении:**

1. **Статус подписки** меняется на `expired`
2. **is_premium** устанавливается в `false`
3. **Лимиты** применяются как для free пользователя:
   - Если карточек > 200 → доступ только для чтения
   - Если профилей > 1 → нельзя создавать новые
   - Лимиты сообщений/упражнений → 50/10 в день
4. **Данные не удаляются** - все карточки, темы, прогресс сохраняются
5. **Отправляется уведомление** пользователю

**Grace period:**

В нашей системе grace period отсутствует — лимиты применяются немедленно после истечения.

### Уведомления об истечении

**За 7 дней:**

```
💎 Ваша Премиум подписка истекает через 7 дней (15 января)

После истечения будут применены ограничения:
• 50 сообщений/день (вместо 500)
• 10 упражнений/день (вместо безлимита)
• Не более 200 карточек

[Продлить подписку →]
```

**За 3 дня:**

```
⚠️ Премиум подписка истекает через 3 дня

Продлите подписку, чтобы сохранить доступ ко всем функциям.

[Продлить сейчас →]
```

**За 1 день:**

```
🚨 Ваша подписка истекает завтра!

Все ваши данные будут сохранены, но применятся ограничения бесплатного плана.

[Продлить подписку →]
```

**После истечения:**

```
❌ Ваша Премиум подписка истекла

Теперь применяются ограничения бесплатного плана:
• 50 сообщений в день
• 10 упражнений в день
• До 200 карточек

Все ваши данные сохранены и доступны.

[Оформить Премиум снова →]
```

**Реализация:**

```python
def send_subscription_expiration_reminders():
    """
    Отправляет напоминания о скором истечении подписки.
    Запускается ежедневно.
    """
    now = datetime.utcnow()

    # За 7 дней
    expires_in_7_days = now + timedelta(days=7)
    send_reminders_for_date(expires_in_7_days, days_remaining=7)

    # За 3 дня
    expires_in_3_days = now + timedelta(days=3)
    send_reminders_for_date(expires_in_3_days, days_remaining=3)

    # За 1 день
    expires_tomorrow = now + timedelta(days=1)
    send_reminders_for_date(expires_tomorrow, days_remaining=1)


def send_reminders_for_date(target_date: datetime, days_remaining: int):
    """
    Отправляет напоминания для подписок, истекающих в определенную дату.
    """
    subscriptions = db.query(Subscription).filter(
        Subscription.status == 'active',
        Subscription.current_period_end >= target_date,
        Subscription.current_period_end < target_date + timedelta(days=1)
    ).all()

    for subscription in subscriptions:
        user = subscription.user

        # Проверяем, не отправляли ли уже уведомление сегодня
        if already_sent_today(user.id, f'subscription_expiring_{days_remaining}d'):
            continue

        # Отправляем уведомление
        send_notification(user, 'subscription_expiring', {
            'days_remaining': days_remaining,
            'expires_at': subscription.current_period_end
        })

        # Помечаем как отправленное
        mark_notification_sent(user.id, f'subscription_expiring_{days_remaining}d')
```

### История подписок и аудит

**Таблица subscription_history:**

```sql
CREATE TABLE subscription_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Event info
    event_type VARCHAR(50) NOT NULL,  -- 'activated', 'renewed', 'canceled', 'expired', 'manual_activation'

    -- Subscription details at the time
    status VARCHAR(20),
    plan VARCHAR(20),
    price DECIMAL(10, 2),
    currency VARCHAR(3),

    -- Metadata
    metadata JSONB,  -- Дополнительные данные (stripe_id, admin_id, reason и т.д.)

    -- Timestamp
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_subscription_history_user_id ON subscription_history(user_id);
CREATE INDEX idx_subscription_history_timestamp ON subscription_history(timestamp);
CREATE INDEX idx_subscription_history_event_type ON subscription_history(event_type);
```

**Логирование событий:**

```python
def log_subscription_event(
    user_id: UUID,
    event_type: str,
    subscription: Subscription = None,
    metadata: dict = None
):
    """
    Логирует событие подписки в историю.
    """
    event = SubscriptionHistory(
        user_id=user_id,
        event_type=event_type,
        status=subscription.status if subscription else None,
        plan=subscription.plan if subscription else None,
        price=subscription.price if subscription else None,
        currency=subscription.currency if subscription else None,
        metadata=metadata or {}
    )

    db.add(event)
    db.commit()

    logger.info(f"Subscription event: user_id={user_id}, type={event_type}")


# Примеры использования
log_subscription_event(user.id, 'activated', subscription, {
    'stripe_subscription_id': subscription.stripe_subscription_id,
    'source': 'stripe_webhook'
})

log_subscription_event(user.id, 'manual_activation', None, {
    'admin_id': str(admin.id),
    'duration_days': 30,
    'reason': 'Compensation for bug'
})

log_subscription_event(user.id, 'expired', subscription, {
    'stripe_subscription_id': subscription.stripe_subscription_id
})
```

**История доступна пользователю:**

```python
@app.get('/api/subscriptions/history')
def get_subscription_history(
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0
):
    """
    Получить историю подписок пользователя.
    """
    history = db.query(SubscriptionHistory).filter(
        SubscriptionHistory.user_id == current_user.id
    ).order_by(
        SubscriptionHistory.timestamp.desc()
    ).limit(limit).offset(offset).all()

    return {
        'data': [serialize_subscription_event(event) for event in history],
        'pagination': {
            'limit': limit,
            'offset': offset,
            'total': db.query(SubscriptionHistory).filter(
                SubscriptionHistory.user_id == current_user.id
            ).count()
        }
    }
```

**Пример ответа:**

```json
{
  "data": [
    {
      "event_type": "activated",
      "status": "active",
      "plan": "yearly",
      "price": "49.00",
      "currency": "EUR",
      "timestamp": "2025-01-08T12:00:00Z",
      "metadata": {
        "stripe_subscription_id": "sub_xxx",
        "source": "stripe_webhook"
      }
    },
    {
      "event_type": "trial_started",
      "status": "trial",
      "timestamp": "2025-01-01T12:00:00Z",
      "metadata": {}
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 2
  }
}
```

---

## Дополнительные API endpoints

### Получить статус подписки

```
GET /api/subscriptions/status
```

**Response (активная подписка):**
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

**Response (free пользователь):**
```json
{
  "is_premium": false,
  "status": "free",
  "trial_available": false,
  "trial_used": true,
  "trial_ended_at": "2025-01-08T00:00:00Z"
}
```

### История платежей (инвойсы)

```
GET /api/subscriptions/invoices
```

**Response:**
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
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 1
  }
}
```

---

Этот документ описывает полную систему монетизации и подписок для Telegram-бота изучения языков с ИИ-преподавателем.
