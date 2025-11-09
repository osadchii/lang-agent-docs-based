# Аутентификация и безопасность

## Общие принципы безопасности

### Цели
1. **Защита user_id** - предотвратить подмену пользователя
2. **Защита данных** - конфиденциальность личных данных и прогресса
3. **Доступ к ресурсам** - пользователь видит только свои данные (кроме групповых материалов)
4. **Соответствие GDPR** - право на удаление данных
5. **Защита от злоупотреблений** - rate limiting, защита от ботов

### Зоны доверия

**Доверенные источники:**
- Telegram Bot API (верифицирует telegram_id автоматически)
- Telegram WebApp API с валидацией initData (HMAC-SHA256)

**Не доверенные:**
- Любые данные от клиента без верификации
- Query parameters в URL (могут быть подделаны)
- localStorage/cookies (можно изменить в DevTools)

---

## 1. Аутентификация

### 1.1. Telegram Authentication

**Два источника аутентификации:**

#### A. Telegram Bot API (для бота)

Telegram сам валидирует все входящие сообщения/команды.

**Процесс:**
1. Пользователь отправляет команду/сообщение боту
2. Telegram верифицирует отправителя
3. Backend получает `Update` объект с проверенным `message.from.user.id`
4. `telegram_id` из этого объекта **всегда валиден**

**Код (псевдокод):**
```python
@bot.message_handler(commands=['start'])
def handle_start(message: types.Message):
    telegram_id = message.from_user.id  # УЖЕ проверен Telegram
    first_name = message.from_user.first_name
    username = message.from_user.username

    # Создаем/обновляем пользователя
    user = get_or_create_user(
        telegram_id=telegram_id,
        first_name=first_name,
        username=username
    )
```

#### B. Telegram Mini App (initData) - **КРИТИЧНО!**

Mini App не имеет автоматической верификации от Telegram. **Без валидации initData любой может подделать telegram_id в запросе!**

**Почему это важно:**
```javascript
// ❌ НЕПРАВИЛЬНО - МОЖНО ПОДДЕЛАТЬ
fetch('/api/users/me', {
  headers: {
    'X-Telegram-ID': '123456789'  // Любой может подставить чужой ID!
  }
})
```

**Правильный процесс:**

1. **Frontend получает initData:**
```javascript
// React Mini App
const initData = window.Telegram.WebApp.initData;
// Это строка типа: "query_id=xxx&user=%7B%22id%22%3A123...&auth_date=1234567890&hash=abc123"
```

2. **Frontend отправляет initData на backend:**
```javascript
const response = await fetch('/api/auth/validate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ init_data: initData })
});

const { token, user } = await response.json();
// Сохраняем JWT token для последующих запросов
localStorage.setItem('jwt_token', token);
```

3. **Backend валидирует initData:**

**Алгоритм валидации HMAC-SHA256:**

```python
import hmac
import hashlib
from urllib.parse import parse_qsl

def validate_telegram_init_data(init_data: str, bot_token: str) -> dict | None:
    """
    Валидирует initData от Telegram WebApp.
    Возвращает данные пользователя или None, если валидация провалилась.
    """
    try:
        # 1. Парсим init_data
        parsed_data = dict(parse_qsl(init_data))

        # 2. Извлекаем hash
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            return None

        # 3. Проверяем auth_date (не старше 1 часа)
        auth_date = int(parsed_data.get('auth_date', 0))
        current_timestamp = int(time.time())
        if current_timestamp - auth_date > 3600:  # 1 час
            return None

        # 4. Создаем data_check_string (сортированные key=value, разделенные \n)
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )

        # 5. Вычисляем secret_key = HMAC-SHA256(bot_token, "WebAppData")
        secret_key = hmac.new(
            key="WebAppData".encode(),
            msg=bot_token.encode(),
            digestmod=hashlib.sha256
        ).digest()

        # 6. Вычисляем expected_hash = HMAC-SHA256(data_check_string, secret_key)
        expected_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        # 7. Сравниваем хеши
        if not hmac.compare_digest(expected_hash, received_hash):
            return None

        # 8. Извлекаем user data
        import json
        user_data = json.loads(parsed_data.get('user', '{}'))

        return {
            'telegram_id': user_data.get('id'),
            'first_name': user_data.get('first_name'),
            'last_name': user_data.get('last_name'),
            'username': user_data.get('username'),
            'language_code': user_data.get('language_code'),
        }

    except Exception as e:
        logger.error(f"initData validation error: {e}")
        return None
```

4. **Backend создает JWT token:**

```python
@app.post('/api/auth/validate')
def validate_init_data(request: InitDataRequest):
    # Валидируем initData
    user_data = validate_telegram_init_data(
        init_data=request.init_data,
        bot_token=settings.BOT_TOKEN
    )

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid initData")

    # Создаем или обновляем пользователя
    user = get_or_create_user(
        telegram_id=user_data['telegram_id'],
        first_name=user_data['first_name'],
        last_name=user_data['last_name'],
        username=user_data['username']
    )

    # Создаем JWT token
    token = create_jwt_token(user)

    return {
        'user': serialize_user(user),
        'token': token,
        'expires_at': datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
```

**Важно:**
- initData действителен только 1 час после генерации (проверка `auth_date`)
- Проверка хеша защищает от подделки данных
- Bot token НЕ передается на frontend (используется только на backend)

---

### 1.2. JWT для REST API

После успешной валидации initData, все последующие запросы используют JWT token.

#### Структура JWT Token

**Header:**
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

**Payload:**
```json
{
  "user_id": "uuid-here",
  "telegram_id": 123456789,
  "is_premium": true,
  "iat": 1234567890,
  "exp": 1234653890
}
```

**Подпись:**
```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  SECRET_KEY
)
```

#### Параметры токена

- **Algorithm:** HS256 (HMAC-SHA256)
- **TTL (Time To Live):** 30 минут
- **Secret Key:** Хранится в переменных окружения, НЕ в коде
- **Refresh:** Нет refresh token в MVP (при истечении - запросить новый через initData)

**Обоснование TTL:**
- 30 минут достаточно для активной сессии пользователя
- Короткий срок повышает безопасность (минимизирует риск при компрометации токена)
- Telegram Mini App позволяет легко перевалидировать через `initData` при необходимости
- Для production можно добавить refresh token со сроком 7 дней для меньшего количества перевалидаций

#### Генерация токена

```python
from datetime import datetime, timedelta
import jwt
from config import settings

def create_jwt_token(user: User) -> str:
    """
    Создает JWT access token для пользователя.

    Args:
        user: Объект пользователя из БД

    Returns:
        JWT token (строка)
    """
    # Время создания и истечения
    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Payload токена
    payload = {
        'user_id': str(user.id),
        'telegram_id': user.telegram_id,
        'is_premium': user.is_premium,
        'iat': int(now.timestamp()),      # issued at
        'exp': int(expires_at.timestamp())  # expiration time
    }

    # Создаем токен
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm='HS256'
    )

    return token
```

**Конфигурация (settings.py):**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    JWT_SECRET_KEY: str  # Генерируется один раз и хранится в .env
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # По умолчанию 30 минут

    class Config:
        env_file = '.env'

settings = Settings()
```

#### Использование токена

**Frontend:**
```javascript
// Добавляем токен ко всем запросам
const response = await fetch('/api/cards', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`,
    'Content-Type': 'application/json'
  }
});
```

**Backend middleware:**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Извлекает и валидирует JWT token, возвращает текущего пользователя.
    """
    token = credentials.credentials

    try:
        # Декодируем JWT
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=['HS256']
        )

        user_id = payload.get('user_id')
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Получаем пользователя из БД
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Использование в endpoints:**
```python
@app.get('/api/users/me')
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    return serialize_user(current_user)

@app.post('/api/cards')
def create_card(
    request: CreateCardRequest,
    current_user: User = Depends(get_current_user)
):
    # current_user уже валидирован и авторизован
    card = create_card_for_user(current_user, request)
    return serialize_card(card)
```

#### Обновление токена

Когда токен истекает (30 минут):

1. Frontend перехватывает 401 ответ
2. Запрашивает новый токен через `/api/auth/validate` с актуальным initData
3. Сохраняет новый токен
4. Повторяет исходный запрос

```javascript
async function fetchWithAuth(url, options = {}) {
  let token = localStorage.getItem('jwt_token');

  let response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
  });

  // Если токен истек
  if (response.status === 401) {
    // Получаем новый токен
    const initData = window.Telegram.WebApp.initData;
    const authResponse = await fetch('/api/auth/validate', {
      method: 'POST',
      body: JSON.stringify({ init_data: initData })
    });

    const { token: newToken } = await authResponse.json();
    localStorage.setItem('jwt_token', newToken);

    // Повторяем запрос с новым токеном
    response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${newToken}`
      }
    });
  }

  return response;
}
```

---

### 1.3. Управление сессиями

#### Активные сессии

**Модель Session (опционально, для продвинутого управления):**

```python
class Session(Base):
    __tablename__ = 'sessions'

    id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey('users.id'), nullable=False)
    jwt_token_hash = Column(String, nullable=False)  # Хеш токена
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow)

    # Информация о клиенте
    user_agent = Column(String)
    ip_address = Column(String)
    device_type = Column(String)  # 'bot' или 'miniapp'

    is_active = Column(Boolean, default=True)
```

**Для нашего MVP:**
- Сессии не храним в БД (stateless JWT)
- Токен хранится на клиенте (localStorage в Mini App)
- При истечении - запрашиваем новый

**Для будущего (если нужно):**
- Возможность просмотра активных сессий
- Возможность отозвать токен (logout)
- Отзыв всех сессий при смене пароля/важных данных

#### Logout

**Mini App:**
```javascript
function logout() {
  localStorage.removeItem('jwt_token');
  // Redirect to start screen
  window.location.href = '/';
}
```

**Backend (если храним сессии):**
```python
@app.post('/api/auth/logout')
def logout(current_user: User = Depends(get_current_user)):
    # Помечаем сессию как неактивную
    session = db.query(Session).filter(
        Session.user_id == current_user.id,
        Session.jwt_token_hash == hash_token(current_token)
    ).first()

    if session:
        session.is_active = False
        db.commit()

    return {'success': True}
```

---

## 2. Авторизация (Authorization)

### 2.1. Роли пользователей

В нашей системе **нет формальных ролей** в таблице `users.role`. Вместо этого используется **контекстная авторизация**:

#### Роли в контексте

**1. Student (все пользователи)**
- Базовая роль - любой зарегистрированный пользователь
- Может управлять своими профилями, колодами, карточками, темами
- Может состоять в группах как участник

**2. Group Owner (владелец группы)**
- Создатель конкретной группы
- Имеет полные права на управление своей группой
- Проверка: `group.owner_id == current_user.id`

**3. Group Member (участник группы)**
- Пользователь, приглашенный в группу
- Может использовать материалы группы
- Проверка: `user.id IN group.members`

**4. Admin (администратор системы)**
- Специальное поле `users.is_admin = true`
- Полный доступ к системе, метрикам, пользователям
- Для внутреннего использования

### 2.2. Разрешения (Permissions)

#### Принципы

1. **Ownership (владение)** - пользователь может изменять только свои ресурсы
2. **Group-based (групповые)** - участники группы имеют read-only доступ к материалам
3. **Subscription-based (подписка)** - premium пользователи имеют расширенные лимиты

#### Матрица доступа

**Карточки (Cards):**

| Действие | Свои карточки | Групповые карточки |
|----------|---------------|---------------------|
| Создать | ✅ (с лимитом) | ❌ |
| Читать | ✅ | ✅ (только просмотр) |
| Изменить | ✅ | ❌ |
| Удалить | ✅ | ❌ |
| Оценивать | ✅ | ✅ (оценки только для себя) |

**Колоды (Decks):**

| Действие | Свои колоды | Групповые колоды |
|----------|-------------|-------------------|
| Создать | ✅ (с лимитом) | ❌ |
| Читать | ✅ | ✅ |
| Изменить | ✅ | ❌ |
| Удалить | ✅ | ❌ |
| Копировать | ✅ | ✅ (создает свою копию) |

**Темы (Topics):**

| Действие | Свои темы | Групповые темы |
|----------|-----------|----------------|
| Создать | ✅ | ❌ |
| Читать | ✅ | ✅ |
| Изменить | ✅ | ❌ |
| Удалить | ✅ | ❌ |

**Группы (Groups):**

| Действие | Владелец | Участник |
|----------|----------|----------|
| Создать группу | ✅ (с лимитом) | ✅ (с лимитом) |
| Читать детали | ✅ | ✅ |
| Изменить группу | ✅ | ❌ |
| Удалить группу | ✅ | ❌ |
| Приглашать участников | ✅ | ❌ |
| Удалять участников | ✅ | ❌ |
| Покинуть группу | ❌ (должен удалить) | ✅ |
| Добавлять материалы | ✅ | ❌ |
| Удалять материалы | ✅ | ❌ |
| Просматривать прогресс участников | ✅ | ❌ (только свой) |

### 2.3. Проверка доступа

#### Middleware и декораторы

**1. Проверка владения ресурсом:**

```python
def check_resource_ownership(
    resource_id: UUID,
    resource_type: str,
    current_user: User = Depends(get_current_user)
):
    """
    Проверяет, что ресурс принадлежит пользователю.
    """
    if resource_type == 'deck':
        resource = db.query(Deck).filter(Deck.id == resource_id).first()
        if not resource or resource.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    elif resource_type == 'card':
        card = db.query(Card).filter(Card.id == resource_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")

        deck = db.query(Deck).filter(Deck.id == card.deck_id).first()
        if deck.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    # и т.д.
```

**2. Проверка роли в группе:**

```python
def check_group_owner(
    group_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Group:
    """
    Проверяет, что пользователь - владелец группы.
    """
    group = db.query(Group).filter(Group.id == group_id).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only group owner can perform this action")

    return group


def check_group_membership(
    group_id: UUID,
    current_user: User = Depends(get_current_user)
) -> tuple[Group, GroupMember]:
    """
    Проверяет, что пользователь - участник или владелец группы.
    """
    group = db.query(Group).filter(Group.id == group_id).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Владелец автоматически считается участником
    if group.owner_id == current_user.id:
        return group, None

    # Проверяем членство
    membership = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(status_code=403, detail="Not a group member")

    return group, membership
```

**3. Проверка лимитов:**

```python
def check_limits(
    limit_type: str,
    current_user: User = Depends(get_current_user)
):
    """
    Проверяет лимиты пользователя (free vs premium).
    """
    limits = get_user_limits(current_user)

    if limit_type == 'profiles':
        if limits['profiles']['used'] >= limits['profiles']['max']:
            raise HTTPException(
                status_code=400,
                detail={
                    'code': 'LIMIT_REACHED',
                    'message': f"Достигнут лимит профилей ({limits['profiles']['max']})",
                    'upgrade_url': '/profile/premium'
                }
            )

    elif limit_type == 'cards':
        if limits['cards']['used'] >= limits['cards']['max']:
            raise HTTPException(status_code=402, detail="Требуется премиум")

    # и т.д.
```

**Использование в endpoints:**

```python
@app.patch('/api/decks/{deck_id}')
def update_deck(
    deck_id: UUID,
    request: UpdateDeckRequest,
    current_user: User = Depends(get_current_user)
):
    # Проверяем ownership
    check_resource_ownership(deck_id, 'deck', current_user)

    # Обновляем колоду
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    deck.name = request.name
    deck.description = request.description
    db.commit()

    return serialize_deck(deck)


@app.post('/api/groups/{group_id}/members')
def invite_member(
    group_id: UUID,
    request: InviteMemberRequest,
    current_user: User = Depends(get_current_user)
):
    # Только владелец может приглашать
    group = check_group_owner(group_id, current_user)

    # Проверяем лимиты группы
    if group.members_count >= group.max_members:
        raise HTTPException(status_code=400, detail="Group is full")

    # Приглашаем участника
    invite = create_group_invite(group, request.user_identifier)
    return serialize_invite(invite)
```

---

## 3. Безопасность данных

### 3.1. Валидация входных данных

#### Принципы валидации

1. **Never trust user input** - всегда валидируем
2. **Whitelist, not blacklist** - разрешаем только известные значения
3. **Type checking** - строгая типизация
4. **Length limits** - ограничения на длину строк
5. **Format validation** - регулярные выражения для email, URL и т.д.

#### Pydantic модели для валидации

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID

class CreateCardRequest(BaseModel):
    deck_id: UUID
    words: list[str] = Field(..., min_items=1, max_items=20)

    @validator('words')
    def validate_words(cls, words):
        # Проверяем, что слова не пустые
        for word in words:
            if not word.strip():
                raise ValueError("Word cannot be empty")
            if len(word) > 100:
                raise ValueError("Word too long (max 100 chars)")
        return [w.strip() for w in words]


class CreateProfileRequest(BaseModel):
    language: str = Field(..., min_length=2, max_length=2, regex=r'^[a-z]{2}$')
    current_level: str = Field(..., regex=r'^(A1|A2|B1|B2|C1|C2)$')
    target_level: str = Field(..., regex=r'^(A1|A2|B1|B2|C1|C2)$')
    goals: list[str] = Field(..., min_items=1, max_items=8)
    interface_language: str = Field(..., regex=r'^(ru|[a-z]{2})$')

    @validator('target_level')
    def validate_target_level(cls, target_level, values):
        current_level = values.get('current_level')
        if current_level and target_level:
            levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
            if levels.index(target_level) < levels.index(current_level):
                raise ValueError("Target level must be >= current level")
        return target_level

    @validator('goals')
    def validate_goals(cls, goals):
        valid_goals = ['work', 'study', 'travel', 'communication',
                      'reading', 'self_development', 'relationships', 'relocation']
        for goal in goals:
            if goal not in valid_goals:
                raise ValueError(f"Invalid goal: {goal}")
        return goals


class CreateGroupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)

    @validator('name')
    def validate_name(cls, name):
        # Удаляем лишние пробелы
        name = ' '.join(name.split())
        if not name:
            raise ValueError("Name cannot be empty")
        return name
```

#### SQL Injection защита

**Всегда используем ORM или параметризованные запросы:**

```python
# ✅ ПРАВИЛЬНО - ORM
user = db.query(User).filter(User.telegram_id == telegram_id).first()

# ✅ ПРАВИЛЬНО - параметризованный запрос
result = db.execute(
    "SELECT * FROM users WHERE telegram_id = :telegram_id",
    {"telegram_id": telegram_id}
)

# ❌ НЕПРАВИЛЬНО - конкатенация строк (SQL Injection!)
result = db.execute(f"SELECT * FROM users WHERE telegram_id = {telegram_id}")
```

#### XSS защита (для текстовых полей)

```python
import bleach

def sanitize_html(text: str) -> str:
    """
    Очищает HTML от опасных тегов.
    """
    allowed_tags = []  # Не разрешаем никакие HTML теги
    return bleach.clean(text, tags=allowed_tags, strip=True)


@app.post('/api/groups')
def create_group(
    request: CreateGroupRequest,
    current_user: User = Depends(get_current_user)
):
    # Санитизация входных данных
    name = sanitize_html(request.name)
    description = sanitize_html(request.description) if request.description else None

    group = Group(
        owner_id=current_user.id,
        name=name,
        description=description
    )
    db.add(group)
    db.commit()

    return serialize_group(group)
```

### 3.2. Rate Limiting

#### Лимиты по категориям

**Per-user лимиты (в день):**

| Ресурс | Free | Premium |
|--------|------|---------|
| LLM сообщения | 50 | 500 |
| Упражнения | 10 | Unlimited |
| Карточки (создание) | 200 total | Unlimited |
| Профили | 1 | 10 |
| Группы | 1 | Unlimited |

**Global лимиты (защита от DDoS):**
- 100 requests/minute per IP
- 1000 requests/hour per user

#### Реализация

**Redis для счетчиков:**

```python
import redis
from datetime import datetime, timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def check_rate_limit(
    user_id: UUID,
    limit_type: str,
    max_requests: int,
    window_seconds: int = 60
) -> tuple[bool, int]:
    """
    Проверяет rate limit.

    Returns:
        (allowed, remaining)
    """
    key = f"rate_limit:{limit_type}:{user_id}"

    # Получаем текущее количество запросов
    current = redis_client.get(key)

    if current is None:
        # Первый запрос в окне
        redis_client.setex(key, window_seconds, 1)
        return True, max_requests - 1

    current = int(current)

    if current >= max_requests:
        # Лимит превышен
        ttl = redis_client.ttl(key)
        return False, 0

    # Инкрементируем счетчик
    redis_client.incr(key)
    return True, max_requests - current - 1


# Middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Извлекаем user из токена
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
    except:
        # Без токена - rate limit по IP
        user_id = request.client.host

    # Проверяем глобальный rate limit
    allowed, remaining = check_rate_limit(
        user_id=user_id,
        limit_type='global',
        max_requests=100,
        window_seconds=60
    )

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                'error': {
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'message': 'Too many requests. Try again in 60 seconds.',
                    'retry_after': 60
                }
            },
            headers={
                'X-RateLimit-Limit': '100',
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': str(int(time.time()) + 60)
            }
        )

    response = await call_next(request)

    # Добавляем headers
    response.headers['X-RateLimit-Limit'] = '100'
    response.headers['X-RateLimit-Remaining'] = str(remaining)

    return response
```

**Специфичные лимиты для LLM:**

```python
def check_llm_limit(user: User) -> bool:
    """
    Проверяет дневной лимит LLM сообщений.
    """
    # Получаем лимиты пользователя
    limits = get_user_limits(user)

    if limits['messages']['used'] >= limits['messages']['max']:
        raise HTTPException(
            status_code=429,
            content={
                'error': {
                    'code': 'LLM_LIMIT_REACHED',
                    'message': f"Достигнут дневной лимит сообщений ({limits['messages']['max']})",
                    'reset_at': limits['messages']['reset_at'],
                    'upgrade_url': '/profile/premium' if not user.is_premium else None
                }
            }
        )

    return True


@app.post('/api/exercises/generate')
def generate_exercise(
    request: GenerateExerciseRequest,
    current_user: User = Depends(get_current_user)
):
    # Проверяем LLM лимит
    check_llm_limit(current_user)

    # Генерируем упражнение через LLM
    exercise = llm_generate_exercise(current_user, request.topic_id, request.type)

    # Инкрементируем счетчик использования
    increment_llm_usage(current_user)

    return exercise
```

### 3.3. Защита от ботов

#### Telegram встроенная защита

Telegram уже защищает от ботов:
- Верификация пользователей при создании аккаунта
- Ограничения на частоту запросов
- Защита от массовой регистрации

#### Дополнительные меры

**1. Анализ поведения:**

```python
def detect_suspicious_activity(user: User) -> bool:
    """
    Определяет подозрительную активность.
    """
    # Слишком быстрое создание карточек
    recent_cards = db.query(Card).filter(
        Card.user_id == user.id,
        Card.created_at >= datetime.utcnow() - timedelta(minutes=5)
    ).count()

    if recent_cards > 50:
        return True

    # Слишком много запросов за короткое время
    # (проверка через Redis rate limiting)

    return False


@app.post('/api/cards')
def create_card(
    request: CreateCardRequest,
    current_user: User = Depends(get_current_user)
):
    # Проверка на бота
    if detect_suspicious_activity(current_user):
        logger.warning(f"Suspicious activity detected: user_id={current_user.id}")
        raise HTTPException(status_code=429, detail="Too many requests")

    # Создаем карточку
    ...
```

**2. Honeypot поля (для веб-форм, если будут):**

```html
<!-- Скрытое поле, которое боты заполнят, а люди - нет -->
<input type="text" name="website" style="display:none" tabindex="-1" autocomplete="off">
```

```python
@app.post('/api/feedback')
def submit_feedback(request: Request):
    # Проверяем honeypot
    if request.form.get('website'):
        # Бот заполнил скрытое поле
        return Response(status_code=200)  # Притворяемся, что все ок

    # Обрабатываем обратную связь
    ...
```

---

## 4. Конфиденциальность (Privacy & GDPR)

### 4.1. Хранение личных данных

#### Что храним

**Обязательные данные (для работы сервиса):**
- `telegram_id` - идентификатор в Telegram
- `first_name` - имя пользователя
- `username` - юзернейм (если есть)
- Языковые профили (язык, уровень, цели)
- Карточки и прогресс обучения
- Групповое членство

**Опциональные данные:**
- `last_name` - фамилия (если предоставлена)
- Email (если запросим для уведомлений)

**НЕ храним:**
- Пароли (аутентификация через Telegram)
- Платежные данные (через Stripe)
- IP адреса (только для rate limiting, временно в Redis)

#### Как защищаем

**1. Шифрование в transit:**
- Все запросы через HTTPS (TLS 1.3)
- Certificate pinning для Mini App (опционально)

**2. Шифрование at rest:**
- Диск БД зашифрован (LUKS или аналог)
- Бэкапы зашифрованы

**3. Доступ к БД:**
- Только backend имеет доступ
- Используем read-only реплики для аналитики
- Audit log для критичных операций

### 4.2. GDPR Compliance

#### Права пользователей

**1. Право на доступ (Right to Access):**

```python
@app.get('/api/users/me/data-export')
def export_user_data(current_user: User = Depends(get_current_user)):
    """
    Экспорт всех данных пользователя в JSON.
    """
    data = {
        'user': {
            'telegram_id': current_user.telegram_id,
            'first_name': current_user.first_name,
            'last_name': current_user.last_name,
            'username': current_user.username,
            'created_at': current_user.created_at.isoformat(),
        },
        'profiles': [
            serialize_profile(p) for p in current_user.profiles
        ],
        'decks': [
            serialize_deck(d) for d in current_user.decks
        ],
        'cards': [
            serialize_card(c) for c in get_all_user_cards(current_user)
        ],
        'groups_owned': [
            serialize_group(g) for g in current_user.owned_groups
        ],
        'groups_member': [
            serialize_group(g) for g in current_user.member_groups
        ],
        'stats': get_user_stats(current_user),
    }

    return JSONResponse(
        content=data,
        headers={
            'Content-Disposition': f'attachment; filename="user_data_{current_user.id}.json"'
        }
    )
```

**2. Право на удаление (Right to Erasure / "Right to be Forgotten"):**

```python
@app.delete('/api/users/me')
def delete_account(
    confirmation: str,
    current_user: User = Depends(get_current_user)
):
    """
    Полное удаление аккаунта и всех связанных данных.
    """
    # Требуем подтверждение
    if confirmation != "DELETE_MY_ACCOUNT":
        raise HTTPException(
            status_code=400,
            detail="Confirmation required"
        )

    # Удаляем данные
    delete_user_data(current_user)

    return {'success': True, 'message': 'Account deleted'}


def delete_user_data(user: User):
    """
    Удаляет все данные пользователя (GDPR compliant).
    """
    # 1. Удаляем карточки
    db.query(Card).filter(Card.user_id == user.id).delete()

    # 2. Удаляем колоды
    db.query(Deck).filter(Deck.user_id == user.id).delete()

    # 3. Удаляем темы
    db.query(Topic).filter(Topic.user_id == user.id).delete()

    # 4. Удаляем профили
    db.query(LanguageProfile).filter(LanguageProfile.user_id == user.id).delete()

    # 5. Группы: если владелец - удаляем группу, если участник - удаляем членство
    for group in user.owned_groups:
        db.delete(group)

    db.query(GroupMember).filter(GroupMember.user_id == user.id).delete()

    # 6. Удаляем историю упражнений
    db.query(ExerciseHistory).filter(ExerciseHistory.user_id == user.id).delete()

    # 7. Удаляем подписку (отменяем в Stripe)
    if user.subscription:
        cancel_stripe_subscription(user.subscription.stripe_subscription_id)
        db.delete(user.subscription)

    # 8. Удаляем самого пользователя
    db.delete(user)

    db.commit()

    logger.info(f"User {user.id} (telegram_id={user.telegram_id}) deleted (GDPR)")
```

**3. Право на исправление (Right to Rectification):**

```python
@app.patch('/api/users/me')
def update_user_info(
    request: UpdateUserRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Обновление личной информации.
    """
    if request.first_name:
        current_user.first_name = request.first_name

    if request.last_name:
        current_user.last_name = request.last_name

    db.commit()

    return serialize_user(current_user)
```

#### Privacy Policy & Terms

**Endpoints для документов:**

```python
@app.get('/api/legal/privacy-policy')
def get_privacy_policy():
    return {
        'version': '1.0',
        'effective_date': '2025-01-01',
        'content': load_privacy_policy()
    }

@app.get('/api/legal/terms-of-service')
def get_terms():
    return {
        'version': '1.0',
        'effective_date': '2025-01-01',
        'content': load_terms()
    }
```

### 4.3. Шифрование

#### TLS/HTTPS

**Обязательно для production:**
- TLS 1.3 или минимум TLS 1.2
- Valid SSL certificate (Let's Encrypt или платный)
- HTTP Strict Transport Security (HSTS) header
- Redirect HTTP → HTTPS

**Nginx конфигурация:**
```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}
```

#### Database Encryption

**Шифрование диска:**
```bash
# LUKS для Linux
cryptsetup luksFormat /dev/sdb
cryptsetup open /dev/sdb postgres_data
mkfs.ext4 /dev/mapper/postgres_data
mount /dev/mapper/postgres_data /var/lib/postgresql/data
```

**PostgreSQL SSL connections:**
```python
# SQLAlchemy connection
engine = create_engine(
    'postgresql://user:password@host/db',
    connect_args={
        'sslmode': 'require',
        'sslrootcert': '/path/to/ca.pem'
    }
)
```

#### Secrets Management

**НЕ храним секреты в коде!**

```python
# ❌ НЕПРАВИЛЬНО
JWT_SECRET = "my-secret-key-123"

# ✅ ПРАВИЛЬНО - переменные окружения
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    JWT_SECRET_KEY: str
    DATABASE_URL: str
    STRIPE_SECRET_KEY: str
    OPENAI_API_KEY: str

    class Config:
        env_file = '.env'

settings = Settings()
```

**.env файл (НЕ коммитим в Git!):**
```bash
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
JWT_SECRET_KEY=super-secret-random-string-256-bits
DATABASE_URL=postgresql://user:pass@localhost/dbname
STRIPE_SECRET_KEY=sk_live_...
OPENAI_API_KEY=sk-...
```

**.gitignore:**
```
.env
.env.local
.env.production
*.pem
*.key
```

**Production: используем Secret Manager:**
- AWS Secrets Manager
- Google Cloud Secret Manager
- HashiCorp Vault
- Или переменные окружения в Docker/K8s

---

## 5. Security Headers

### 5.1. HTTP Security Headers

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Защита от XSS
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # HSTS (для HTTPS)
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    # CSP (Content Security Policy)
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.telegram.org"
    )

    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # Permissions Policy
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

    return response
```

---

## 6. Monitoring & Incident Response

### 6.1. Security Logging

```python
import logging

security_logger = logging.getLogger('security')

# Логируем важные события
def log_security_event(event_type: str, user_id: UUID, details: dict):
    security_logger.warning(
        f"Security Event: {event_type}",
        extra={
            'event_type': event_type,
            'user_id': str(user_id),
            'timestamp': datetime.utcnow().isoformat(),
            **details
        }
    )


# Примеры использования
log_security_event('auth_failed', user_id, {'reason': 'invalid_token'})
log_security_event('suspicious_activity', user_id, {'cards_created': 50, 'timeframe': '5min'})
log_security_event('rate_limit_exceeded', user_id, {'endpoint': '/api/exercises/generate'})
```

### 6.2. Alerts

**Настроить оповещения на:**
- Множественные неудачные попытки аутентификации
- Превышение rate limits
- Подозрительная активность (массовое создание ресурсов)
- Ошибки 500 (могут указывать на атаку)

---

## Чеклист безопасности

**Перед деплоем в production:**

- [ ] Telegram initData валидация реализована и тестирована
- [ ] JWT секрет сгенерирован (256+ бит) и хранится в Secret Manager
- [ ] HTTPS настроен с валидным сертификатом
- [ ] HSTS header включен
- [ ] CORS настроен правильно (только telegram.org)
- [ ] Rate limiting работает (Redis)
- [ ] Валидация всех входных данных через Pydantic
- [ ] SQL queries используют ORM или параметризованы
- [ ] XSS защита для текстовых полей
- [ ] Security headers установлены
- [ ] Secrets не коммитятся в Git (.env в .gitignore)
- [ ] Логирование security events настроено
- [ ] Backup БД настроен и зашифрован
- [ ] Privacy Policy и Terms размещены
- [ ] Endpoint для удаления аккаунта (GDPR) работает
- [ ] Monitoring и alerting настроены

---

Этот документ описывает полную систему аутентификации и безопасности для Telegram-бота изучения языков с ИИ-преподавателем.
