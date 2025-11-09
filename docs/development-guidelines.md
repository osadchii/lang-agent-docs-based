# Принципы разработки

## Общие принципы

### Соответствие документации
**КРИТИЧНО:** Вся разработка ведется В ТОЧНОМ соответствии с проектной документацией:

- **Перед началом работы** над задачей ОБЯЗАТЕЛЬНО изучить релевантные документы из `docs/`
- **Архитектурные решения** должны соответствовать `architecture.md`
- **API endpoints** должны строго следовать спецификации из `backend-api.md`
- **Компоненты UI** должны соответствовать описанию в `frontend-structure.md` и `frontend-screens.md`
- **Бизнес-логика** должна реализовывать use cases из `use-cases.md`
- **При несоответствии документации и кода** - приоритет у документации (либо документация должна быть обновлена через согласованный процесс)

### Принцип малых файлов и ограниченной ответственности

**Правило:** Один файл = одна ответственность

**Backend (Python):**
- **Максимум 300 строк** на файл (исключение: модели данных до 400 строк)
- **Один класс на файл** (исключение: тесно связанные классы типа Request/Response models)
- **Максимум 5-7 публичных методов** на класс
- **Методы до 50 строк** (сложные методы разбиваются на приватные подметоды)

**Frontend (TypeScript/React):**
- **Максимум 250 строк** на компонент
- **Один компонент на файл**
- **Максимум 5 props** (если больше - создать объект конфигурации)
- **Максимум 3 хука** в компоненте (если больше - выделить в custom hook)

**Признаки что файл нужно разделить:**
- Импорты занимают > 20 строк
- Более 3 уровней вложенности условий/циклов
- Дублирование кода внутри файла
- Сложность тестирования (мокирование > 5 зависимостей)

### Документирование и расширяемость

**Каждый файл должен содержать:**
1. **Заголовок с описанием модуля** (что делает, зачем нужен)
2. **Примеры использования** (в docstring или README)
3. **Описание публичного API** (параметры, возвращаемые значения, исключения)
4. **TODO markers** для известных ограничений

**Комментарии должны объяснять "ПОЧЕМУ", а не "ЧТО":**
```python
# ❌ Плохо
# Проверяем что user_id существует
if not user_id:
    raise ValueError()

# ✅ Хорошо
# Telegram может передать пустой user_id при ошибке валидации initData
# В этом случае мы не можем безопасно идентифицировать пользователя
if not user_id:
    raise AuthenticationError("Invalid Telegram initData: missing user_id")
```

### Тестовое покрытие

**ОБЯЗАТЕЛЬНЫЕ требования:**

**Backend:**
- **Минимум 85%** общего покрытия
- **100%** покрытие критичных модулей:
  - Authentication (auth_service.py)
  - Payment processing (subscription_service.py)
  - Data access layer (repositories)
- **Все edge cases** должны быть покрыты тестами

**Frontend:**
- **Минимум 75%** общего покрытия
- **100%** покрытие критичных компонентов:
  - Authentication flow
  - Payment flow
  - CardStudySession
  - ExerciseSession
- **Все пользовательские сценарии** из `use-cases.md` должны иметь E2E тесты (опционально Playwright)

**Уровни тестирования:**
1. **Unit tests** - изолированные тесты функций/классов
2. **Integration tests** - тесты взаимодействия между модулями
3. **API tests** - тесты REST API endpoints
4. **Component tests** - тесты React компонентов
5. **E2E tests** - тесты полных пользовательских сценариев

**Проверка тестов:**
- **Перед каждым коммитом** - запуск всех юнит-тестов
- **Перед PR** - запуск всех тестов (включая интеграционные)
- **CI/CD pipeline** - автоматический запуск всех тестов
- **Перед деплоем** - обязательное прохождение всех тестов

---

## Code Style

### Python (Backend)

#### Форматирование
- **PEP 8** - базовый стандарт
- **Black** для автоматического форматирования:
  ```bash
  black --line-length 100 backend/
  ```
- **isort** для сортировки импортов:
  ```bash
  isort --profile black backend/
  ```

#### Линтинг
- **Ruff** (замена Flake8, pylint, mypy):
  ```bash
  ruff check backend/
  ```
- Конфигурация в `pyproject.toml`:
  ```toml
  [tool.ruff]
  line-length = 100
  target-version = "py311"
  select = ["E", "F", "I", "N", "W", "B", "ANN", "S", "C90"]
  ignore = ["ANN101", "ANN102"]  # Не требовать type hints для self, cls
  ```

#### Type Hints
**ОБЯЗАТЕЛЬНО** для всех:
- Параметров функций
- Возвращаемых значений
- Переменных класса
- Публичных переменных модуля

```python
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

def create_card(
    word: str,
    deck_id: UUID,
    profile_id: UUID,
    translation: Optional[str] = None
) -> Card:
    """
    Создать новую карточку.

    Args:
        word: Слово на изучаемом языке
        deck_id: ID колоды
        profile_id: ID языкового профиля
        translation: Перевод (если None - будет сгенерирован через LLM)

    Returns:
        Созданная карточка

    Raises:
        DuplicateCardError: Если карточка с такой леммой уже существует
        LimitReachedError: Если достигнут лимит карточек для пользователя
    """
    pass
```

#### Docstrings
**Google Style** для всех публичных функций и классов:

```python
class FlashcardsService:
    """
    Сервис для работы с флеш-карточками.

    Отвечает за создание карточек, генерацию контента через LLM,
    управление интервальным повторением (SM-2 алгоритм).

    Attributes:
        llm_service: Сервис для работы с LLM
        card_repo: Репозиторий карточек

    Example:
        >>> service = FlashcardsService(llm_service, card_repo)
        >>> card = await service.create_card("casa", deck_id, profile_id)
        >>> print(card.translation)  # "дом"
    """

    def __init__(
        self,
        llm_service: LLMService,
        card_repo: CardRepository
    ) -> None:
        self.llm_service = llm_service
        self.card_repo = card_repo
```

#### Структура файла
```python
"""
Модуль для работы с флеш-карточками.

Содержит сервисный слой для создания, обновления и изучения карточек.
Использует SM-2 алгоритм для интервального повторения.
"""

# Standard library
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta

# Third-party
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

# Local
from app.models.card import Card
from app.repositories.card_repository import CardRepository
from app.services.llm_service import LLMService
from app.exceptions import DuplicateCardError, LimitReachedError


class FlashcardsService:
    """Сервис для работы с флеш-карточками."""

    # ... implementation
```

#### Именование
- **Classes**: `PascalCase` - `UserService`, `CardRepository`
- **Functions/Methods**: `snake_case` - `create_card`, `get_next_due`
- **Constants**: `UPPER_SNAKE_CASE` - `MAX_CARDS_FREE`, `DEFAULT_INTERVAL_DAYS`
- **Private**: `_leading_underscore` - `_calculate_interval`, `_validate_lemma`

#### Максимальная длина
- **Строка**: 100 символов
- **Функция/метод**: 50 строк (разбивать на подметоды если больше)
- **Файл**: 300 строк (разделять на модули если больше)

---

### TypeScript/React (Frontend)

#### Форматирование
- **Prettier** для автоматического форматирования:
  ```json
  {
    "semi": true,
    "singleQuote": true,
    "tabWidth": 2,
    "trailingComma": "es5",
    "printWidth": 100,
    "arrowParens": "always"
  }
  ```

#### Линтинг
- **ESLint** с конфигурацией:
  ```json
  {
    "extends": [
      "eslint:recommended",
      "plugin:@typescript-eslint/recommended",
      "plugin:react/recommended",
      "plugin:react-hooks/recommended",
      "plugin:jsx-a11y/recommended",
      "prettier"
    ],
    "rules": {
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/explicit-function-return-type": "warn",
      "react/prop-types": "off",
      "react-hooks/exhaustive-deps": "error"
    }
  }
  ```

#### Type Safety
**ЗАПРЕЩЕНО использовать:**
- `any` (использовать `unknown` если тип действительно неизвестен)
- `@ts-ignore` (использовать `@ts-expect-error` с комментарием)
- Type assertions `as` без необходимости

```typescript
// ❌ Плохо
const data: any = await fetchData();
const user = data as User;

// ✅ Хорошо
interface ApiResponse<T> {
  data: T;
  error?: string;
}

const response: ApiResponse<User> = await fetchData();
if (response.error) {
  throw new Error(response.error);
}
const user = response.data;
```

#### Component Structure
```typescript
/**
 * Компонент карточки для изучения слов.
 *
 * Отображает слово на одной стороне и перевод на другой.
 * Поддерживает 3D flip анимацию и haptic feedback.
 *
 * @example
 * <FlashCard
 *   word="casa"
 *   translation="дом"
 *   onFlip={handleFlip}
 * />
 */

import { FC, useState } from 'react';
import { motion } from 'framer-motion';
import { useHaptic } from '@/hooks/useHaptic';
import styles from './FlashCard.module.css';

interface FlashCardProps {
  word: string;
  translation: string;
  example: string;
  exampleTranslation: string;
  onFlip: () => void;
}

export const FlashCard: FC<FlashCardProps> = ({
  word,
  translation,
  example,
  exampleTranslation,
  onFlip,
}) => {
  const [isFlipped, setIsFlipped] = useState(false);
  const { impactOccurred } = useHaptic();

  const handleFlip = (): void => {
    impactOccurred('light');
    setIsFlipped((prev) => !prev);
    onFlip();
  };

  return (
    <motion.div
      className={styles.card}
      onClick={handleFlip}
      animate={{ rotateY: isFlipped ? 180 : 0 }}
      transition={{ duration: 0.6 }}
    >
      {/* ... implementation */}
    </motion.div>
  );
};
```

#### Hooks Rules
- **Используйте только функциональные компоненты**
- **Custom hooks** начинаются с `use`
- **Следуйте Rules of Hooks** (только на верхнем уровне)
- **Мемоизируйте** сложные вычисления с `useMemo`
- **Используйте `useCallback`** для функций передаваемых в пропсы

```typescript
// src/hooks/useCards.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cardsApi } from '@/api/endpoints/cards';
import type { Card, CardRating } from '@/types/api';

/**
 * Хук для работы с карточками.
 *
 * Предоставляет методы для получения и оценки карточек
 * с автоматическим кэшированием и оптимистичными обновлениями.
 */
export const useCards = (deckId: string) => {
  const queryClient = useQueryClient();

  const { data: cards, isLoading } = useQuery({
    queryKey: ['cards', deckId],
    queryFn: () => cardsApi.getCards(deckId),
    staleTime: 2 * 60 * 1000, // 2 минуты
  });

  const rateCardMutation = useMutation({
    mutationFn: ({ cardId, rating }: { cardId: string; rating: CardRating }) =>
      cardsApi.rateCard(cardId, rating),
    onSuccess: () => {
      // Invalidate cache
      queryClient.invalidateQueries({ queryKey: ['cards', deckId] });
    },
  });

  return {
    cards,
    isLoading,
    rateCard: rateCardMutation.mutate,
  };
};
```

#### Именование
- **Components**: `PascalCase` - `FlashCard`, `BottomNav`
- **Hooks**: `camelCase` с префиксом `use` - `useCards`, `useTelegram`
- **Functions**: `camelCase` - `handleClick`, `formatDate`
- **Constants**: `UPPER_SNAKE_CASE` - `API_BASE_URL`, `MAX_RETRY_COUNT`
- **Types/Interfaces**: `PascalCase` - `User`, `CardProps`

#### File Organization
```
FlashCard/
├── FlashCard.tsx          # Компонент
├── FlashCard.module.css   # Стили
├── FlashCard.test.tsx     # Тесты
├── index.ts               # Re-export
└── types.ts               # Types (если много)
```

---

## Git Workflow

### Branch Strategy

**Main Branches:**
- **`main`** - продакшн, всегда стабильный, защищен от прямых пушей
- **`develop`** - интеграционная ветка для разработки (опционально)

**Feature Branches:**
- **`feature/{ticket-id}-{short-description}`** - новые фичи
  - Примеры: `feature/LANG-123-flashcard-component`, `feature/LANG-456-user-auth`
- **`bugfix/{ticket-id}-{short-description}`** - баг-фиксы
  - Примеры: `bugfix/LANG-789-fix-card-flip-animation`
- **`hotfix/{ticket-id}-{short-description}`** - критичные исправления для продакшена
  - Создаются от `main`, мержатся обратно в `main` и `develop`

**Правила:**
- Ветки создаются от `develop` (или `main` для hotfix)
- Имя ветки должно быть lowercase с дефисами
- После мержа ветка удаляется

### Commit Messages (Conventional Commits)

**Формат:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - новая функциональность
- `fix` - исправление бага
- `docs` - изменения в документации
- `style` - форматирование, отсутствующие точки с запятой и т.д. (не влияет на логику)
- `refactor` - рефакторинг кода без изменения функциональности
- `perf` - улучшение производительности
- `test` - добавление или исправление тестов
- `chore` - изменения в build process, инструментах, зависимостях
- `ci` - изменения в CI/CD конфигурации

**Scope** (опционально):
- `backend`, `frontend`, `api`, `auth`, `cards`, `exercises`, `groups`, `db`, `ci`

**Examples:**
```bash
# Новая функциональность
git commit -m "feat(cards): add flip animation with haptic feedback"

# Исправление бага
git commit -m "fix(auth): validate Telegram initData timestamp"

# Рефакторинг
git commit -m "refactor(services): extract SM-2 algorithm to separate class"

# Breaking change
git commit -m "feat(api): change cards endpoint response format

BREAKING CHANGE: cards endpoint now returns pagination object"

# С номером тикета
git commit -m "feat(cards): add card rating functionality

Implements SM-2 algorithm for spaced repetition.

Refs: LANG-123"
```

**Правила:**
- Subject в imperative mood ("add" не "added")
- Subject без точки в конце
- Subject до 72 символов
- Body объясняет "что" и "почему", не "как"
- Footer для breaking changes, closes issues

### Pull Requests

#### Требования к PR

**Перед созданием PR:**
1. ✅ Все тесты проходят локально
2. ✅ Код отформатирован (Black/Prettier)
3. ✅ Нет ошибок линтера
4. ✅ Добавлены/обновлены тесты
5. ✅ Обновлена документация (если требуется)
6. ✅ Ветка rebased на актуальный `develop`

**Название PR:**
```
[LANG-123] Add flashcard flip animation
```

**Описание PR (template):**
```markdown
## Описание
Краткое описание изменений (2-3 предложения).

## Связанные задачи
- Closes #123
- Refs #456

## Тип изменений
- [ ] Новая функциональность
- [ ] Исправление бага
- [ ] Рефакторинг
- [ ] Улучшение производительности
- [ ] Breaking change

## Чеклист
- [ ] Код соответствует code style guidelines
- [ ] Добавлены/обновлены тесты (покрытие ≥ 85%)
- [ ] Все тесты проходят
- [ ] Обновлена документация
- [ ] Проверена работа на разных устройствах/браузерах
- [ ] Нет console.log/debugger в коде
- [ ] Нет закомментированного кода

## Тестирование
Описание как протестировать изменения:
1. Открыть Mini App
2. Перейти на страницу карточек
3. Нажать на карточку
4. Убедиться что анимация плавная и есть haptic feedback

## Screenshots/Videos
(если применимо)

## Breaking Changes
(если есть breaking changes, описать migration path)
```

#### Процесс Review

**Code Review Checklist:**

1. **Соответствие документации**
   - [ ] Реализация соответствует спецификации из `docs/`
   - [ ] API endpoints соответствуют `backend-api.md`
   - [ ] Используются правильные модели данных

2. **Архитектура**
   - [ ] Соблюдается layered architecture (handlers → services → repositories)
   - [ ] Нет смешивания уровней ответственности
   - [ ] Зависимости инжектируются правильно
   - [ ] Файлы < 300 строк (backend) / < 250 строк (frontend)

3. **Код**
   - [ ] Читаемость и понятность
   - [ ] Нет дублирования кода (DRY)
   - [ ] Следование принципам SOLID
   - [ ] Корректная обработка ошибок
   - [ ] Нет захардкоженных значений (использованы константы)

4. **Безопасность**
   - [ ] Валидация всех входных данных
   - [ ] Нет SQL injection, XSS уязвимостей
   - [ ] Правильная валидация Telegram initData
   - [ ] Проверка authorization для endpoints
   - [ ] Нет логирования чувствительных данных

5. **Тестирование**
   - [ ] Покрытие тестами ≥ 85%
   - [ ] Юнит-тесты для бизнес-логики
   - [ ] Интеграционные тесты для API
   - [ ] Проверены edge cases
   - [ ] Тесты понятны и поддерживаемы

6. **Производительность**
   - [ ] Нет N+1 запросов
   - [ ] Используются индексы БД
   - [ ] Нет ненужных ре-рендеров (React)
   - [ ] Асинхронные операции где возможно

7. **Документация**
   - [ ] Docstrings/JSDoc для публичных API
   - [ ] Комментарии для сложной логики
   - [ ] README обновлен (если нужно)
   - [ ] Типы корректно описаны

**Процесс:**
1. PR создается → автоматически запускаются CI тесты
2. Минимум **2 approvals** от других разработчиков
3. Все комментарии должны быть resolved
4. CI pipeline успешно пройден
5. Squash and merge в `develop`
6. Удаление feature branch

---

## Архитектурные принципы

### Backend: Layered Architecture

```
┌─────────────────────────────────────────┐
│          API Layer (FastAPI)            │  ← Валидация, сериализация, роутинг
├─────────────────────────────────────────┤
│  Handlers (Bot + REST API)              │  ← Обработка requests, формирование responses
├─────────────────────────────────────────┤
│  Business Logic (Services)              │  ← Бизнес-логика, оркестрация
├─────────────────────────────────────────┤
│  Data Access (Repositories)             │  ← CRUD операции, query building
├─────────────────────────────────────────┤
│  Models (SQLAlchemy ORM)                │  ← Модели данных
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│      Database (PostgreSQL)              │
└─────────────────────────────────────────┘
```

**Правила:**
1. **Handlers** не содержат бизнес-логики, только:
   - Валидация входных данных
   - Вызов сервисов
   - Формирование ответа
   - Обработка исключений

2. **Services** содержат всю бизнес-логику:
   - Оркестрация между repositories
   - Валидация бизнес-правил
   - Вызов внешних сервисов (LLM, Stripe)
   - Управление транзакциями

3. **Repositories** работают с БД:
   - CRUD операции
   - Query building
   - Маппинг моделей
   - Никакой бизнес-логики

4. **Models** - только определение структуры:
   - Поля, типы, constraints
   - Relationships
   - Никакой логики (кроме простых properties)

**Пример:**
```python
# ❌ ПЛОХО - бизнес-логика в handler
@router.post("/cards")
async def create_card(data: CreateCardRequest):
    # Проверка дубликата
    existing = await db.query(Card).filter(
        Card.lemma == get_lemma(data.word)
    ).first()
    if existing:
        raise HTTPException(400, "Duplicate")

    # Генерация перевода
    translation = await llm_service.generate_translation(data.word)

    # Сохранение
    card = Card(word=data.word, translation=translation)
    db.add(card)
    await db.commit()
    return card


# ✅ ХОРОШО - handler только координирует
@router.post("/cards")
async def create_card(
    data: CreateCardRequest,
    service: FlashcardsService = Depends()
):
    """Create a new flashcard."""
    try:
        card = await service.create_card(
            word=data.word,
            deck_id=data.deck_id,
            profile_id=data.profile_id
        )
        return CardResponse.from_orm(card)
    except DuplicateCardError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except LimitReachedError as e:
        raise HTTPException(status_code=402, detail=str(e))
```

### Dependency Injection

**Использовать FastAPI Depends:**

```python
# app/dependencies.py

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status

from app.database import get_db_session
from app.services.flashcards_service import FlashcardsService
from app.services.llm_service import LLMService
from app.repositories.card_repository import CardRepository
from app.core.auth import get_current_user


async def get_card_repository(
    session: AsyncSession = Depends(get_db_session)
) -> CardRepository:
    """Provide card repository."""
    return CardRepository(session)


async def get_llm_service() -> LLMService:
    """Provide LLM service."""
    return LLMService()


async def get_flashcards_service(
    card_repo: CardRepository = Depends(get_card_repository),
    llm_service: LLMService = Depends(get_llm_service)
) -> FlashcardsService:
    """Provide flashcards service."""
    return FlashcardsService(
        card_repo=card_repo,
        llm_service=llm_service
    )


# Использование в endpoint
@router.post("/cards")
async def create_card(
    data: CreateCardRequest,
    user: User = Depends(get_current_user),
    service: FlashcardsService = Depends(get_flashcards_service)
):
    card = await service.create_card(...)
    return card
```

### Frontend: Component Architecture

**Структура компонентов:**

```
src/components/
├── ui/                  # Generic UI components (Button, Input, etc.)
├── layout/              # Layout components (Header, BottomNav)
├── flashcards/          # Domain-specific flashcard components
├── exercises/           # Domain-specific exercise components
└── shared/              # Shared utilities (ErrorBoundary, Loader)
```

**Принципы:**
1. **Composition over inheritance** - компоненты комбинируются, не наследуются
2. **Container/Presentational pattern** - разделение логики и представления
3. **Single Responsibility** - один компонент = одна задача
4. **Props down, events up** - данные передаются вниз, события вверх

**Пример:**
```typescript
// ❌ ПЛОХО - смешана логика и представление
export const FlashCardPage: FC = () => {
  const [cards, setCards] = useState<Card[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);

  useEffect(() => {
    fetchCards().then(setCards);
  }, []);

  const handleRate = async (rating: CardRating) => {
    await rateCard(cards[currentIndex].id, rating);
    setCurrentIndex(prev => prev + 1);
  };

  // ... render logic
};


// ✅ ХОРОШО - разделение на container и presentational
// Container (логика)
export const FlashCardPage: FC = () => {
  const { deckId } = useParams();
  const { cards, isLoading } = useCards(deckId);
  const { currentCard, nextCard, rateCard } = useCardStudySession(cards);

  if (isLoading) return <LoadingScreen />;
  if (!currentCard) return <CompletedScreen />;

  return (
    <CardStudySession
      card={currentCard}
      onRate={(rating) => {
        rateCard(currentCard.id, rating);
        nextCard();
      }}
    />
  );
};

// Presentational (UI)
interface CardStudySessionProps {
  card: Card;
  onRate: (rating: CardRating) => void;
}

export const CardStudySession: FC<CardStudySessionProps> = ({ card, onRate }) => {
  const [isFlipped, setIsFlipped] = useState(false);

  return (
    <div>
      <FlashCard {...card} isFlipped={isFlipped} onFlip={() => setIsFlipped(true)} />
      <CardRatingButtons onRate={onRate} disabled={!isFlipped} />
    </div>
  );
};
```

---

## Тестирование

### Backend Testing (Python + Pytest)

#### Структура тестов
```
backend/
├── tests/
│   ├── unit/                    # Unit tests
│   │   ├── services/
│   │   │   ├── test_flashcards_service.py
│   │   │   ├── test_llm_service.py
│   │   │   └── test_auth_service.py
│   │   ├── repositories/
│   │   └── utils/
│   │
│   ├── integration/             # Integration tests
│   │   ├── test_api_cards.py
│   │   ├── test_api_exercises.py
│   │   └── test_database.py
│   │
│   ├── e2e/                     # End-to-end tests
│   │   └── test_user_flows.py
│   │
│   ├── conftest.py              # Shared fixtures
│   └── factories.py             # Test data factories
```

#### Unit Tests (Services, Utilities)

**Требования:**
- Изолированность (мокируются все зависимости)
- Быстрота (< 100ms на тест)
- Покрытие всех edge cases
- Тестирование одной функции/метода

**Пример:**
```python
# tests/unit/services/test_flashcards_service.py

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from app.services.flashcards_service import FlashcardsService
from app.exceptions import DuplicateCardError, LimitReachedError
from tests.factories import CardFactory, ProfileFactory


class TestFlashcardsService:
    """Тесты для FlashcardsService."""

    @pytest.fixture
    def mock_card_repo(self):
        """Mock card repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service."""
        mock = Mock()
        mock.generate_card_content = AsyncMock(return_value={
            "translation": "дом",
            "example": "Mi casa es tu casa",
            "example_translation": "Мой дом - твой дом"
        })
        return mock

    @pytest.fixture
    def service(self, mock_card_repo, mock_llm_service):
        """Create service instance with mocked dependencies."""
        return FlashcardsService(
            card_repo=mock_card_repo,
            llm_service=mock_llm_service
        )

    @pytest.mark.asyncio
    async def test_create_card_success(self, service, mock_card_repo, mock_llm_service):
        """Тест успешного создания карточки."""
        # Arrange
        word = "casa"
        deck_id = uuid4()
        profile_id = uuid4()

        mock_card_repo.get_by_lemma.return_value = None  # Нет дубликата
        mock_card_repo.create.return_value = CardFactory.build(word=word)

        # Act
        card = await service.create_card(word, deck_id, profile_id)

        # Assert
        assert card.word == word
        assert card.translation == "дом"
        mock_llm_service.generate_card_content.assert_called_once_with(
            word="casa",
            language="es",
            level="A2"
        )
        mock_card_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_card_duplicate_raises_error(self, service, mock_card_repo):
        """Тест что дубликат вызывает ошибку."""
        # Arrange
        word = "casa"
        existing_card = CardFactory.build(word=word, lemma="casa")
        mock_card_repo.get_by_lemma.return_value = existing_card

        # Act & Assert
        with pytest.raises(DuplicateCardError) as exc_info:
            await service.create_card(word, uuid4(), uuid4())

        assert "casa" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rate_card_know_increases_interval(self, service, mock_card_repo):
        """Тест что оценка 'know' увеличивает интервал."""
        # Arrange
        card = CardFactory.build(interval_days=1)
        mock_card_repo.get.return_value = card

        # Act
        updated_card = await service.rate_card(card.id, "know")

        # Assert
        assert updated_card.interval_days > 1  # SM-2 должен увеличить
        mock_card_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_card_dont_know_resets_interval(self, service, mock_card_repo):
        """Тест что оценка 'dont_know' сбрасывает интервал."""
        # Arrange
        card = CardFactory.build(interval_days=10)
        mock_card_repo.get.return_value = card

        # Act
        updated_card = await service.rate_card(card.id, "dont_know")

        # Assert
        assert updated_card.interval_days == 1  # Сброс на 1 день
```

#### Integration Tests (API, Database)

**Требования:**
- Тестируют взаимодействие между слоями
- Используют реальную тестовую БД (SQLite in-memory или PostgreSQL test instance)
- Проверяют полные флоу

**Пример:**
```python
# tests/integration/test_api_cards.py

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User
from app.models.card import Card
from tests.factories import UserFactory, DeckFactory


@pytest.mark.integration
class TestCardsAPI:
    """Интеграционные тесты для Cards API."""

    @pytest.fixture
    async def client(self):
        """HTTP client."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    async def authenticated_user(self, db_session: AsyncSession):
        """Create authenticated user."""
        user = UserFactory.create()
        db_session.add(user)
        await db_session.commit()
        return user

    @pytest.fixture
    async def auth_headers(self, authenticated_user):
        """Generate auth headers with JWT token."""
        token = create_access_token(authenticated_user.id)
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_create_card_returns_201(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession
    ):
        """Тест создания карточки возвращает 201."""
        # Arrange
        deck = DeckFactory.create()
        db_session.add(deck)
        await db_session.commit()

        payload = {
            "deck_id": str(deck.id),
            "words": ["casa"]
        }

        # Act
        response = await client.post(
            "/api/cards",
            json=payload,
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert len(data["created"]) == 1
        assert data["created"][0]["word"] == "casa"
        assert data["created"][0]["translation"] is not None

        # Verify DB
        card = await db_session.get(Card, data["created"][0]["id"])
        assert card is not None
        assert card.word == "casa"

    @pytest.mark.asyncio
    async def test_create_card_duplicate_returns_409(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession
    ):
        """Тест создания дубликата возвращает 409."""
        # Arrange
        deck = DeckFactory.create()
        existing_card = CardFactory.create(deck=deck, lemma="casa")
        db_session.add_all([deck, existing_card])
        await db_session.commit()

        payload = {
            "deck_id": str(deck.id),
            "words": ["casa"]
        }

        # Act
        response = await client.post(
            "/api/cards",
            json=payload,
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert len(data["duplicates"]) == 1
        assert len(data["created"]) == 0
```

#### Test Fixtures и Factories

**Использовать Factory Boy:**

```python
# tests/factories.py

import factory
from factory.fuzzy import FuzzyChoice
from datetime import datetime
from uuid import uuid4

from app.models.user import User
from app.models.profile import LanguageProfile
from app.models.card import Card


class UserFactory(factory.Factory):
    """Factory for User model."""

    class Meta:
        model = User

    id = factory.LazyFunction(uuid4)
    telegram_id = factory.Sequence(lambda n: 100000000 + n)
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    username = factory.Faker('user_name')
    is_premium = False
    created_at = factory.LazyFunction(datetime.utcnow)


class LanguageProfileFactory(factory.Factory):
    """Factory for LanguageProfile model."""

    class Meta:
        model = LanguageProfile

    id = factory.LazyFunction(uuid4)
    user = factory.SubFactory(UserFactory)
    language = "es"
    current_level = "A2"
    target_level = "B2"
    goals = ["travel", "work"]
    is_active = True


class CardFactory(factory.Factory):
    """Factory for Card model."""

    class Meta:
        model = Card

    id = factory.LazyFunction(uuid4)
    word = factory.Faker('word')
    translation = factory.Faker('word', locale='ru_RU')
    lemma = factory.LazyAttribute(lambda obj: obj.word.lower())
    status = FuzzyChoice(['new', 'learning', 'review'])
    interval_days = 1
    next_review = factory.LazyFunction(datetime.utcnow)
```

**Shared Fixtures (conftest.py):**

```python
# tests/conftest.py

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.core.config import settings


@pytest_asyncio.fixture
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create test database session."""
    async_session = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()
```

#### Coverage Requirements

**Запуск тестов с покрытием:**
```bash
# Все тесты
pytest --cov=app --cov-report=html --cov-report=term

# Только unit tests
pytest tests/unit/ --cov=app/services --cov=app/utils

# С минимальным покрытием
pytest --cov=app --cov-fail-under=85
```

**Минимальное покрытие:**
- **Критичные модули: 100%**
  - `app/services/auth_service.py`
  - `app/services/subscription_service.py`
  - `app/repositories/`
- **Сервисы: 90%**
- **Handlers/API: 85%**
- **Utils: 85%**
- **Overall: 85%**

---

### Frontend Testing (TypeScript + Vitest + RTL)

#### Структура тестов
```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/
│   │   │   └── Button/
│   │   │       ├── Button.tsx
│   │   │       └── Button.test.tsx
│   │   └── flashcards/
│   │       └── FlashCard/
│   │           ├── FlashCard.tsx
│   │           └── FlashCard.test.tsx
│   │
│   ├── hooks/
│   │   ├── useCards.ts
│   │   └── useCards.test.ts
│   │
│   └── utils/
│       ├── date.ts
│       └── date.test.ts
│
└── tests/
    ├── setup.ts              # Test setup
    ├── mocks/                # Mock data, MSW handlers
    └── e2e/                  # Playwright E2E tests
```

#### Unit Tests (Utilities, Hooks)

**Пример тестирования utility:**
```typescript
// src/utils/date.test.ts

import { describe, it, expect } from 'vitest';
import { formatDate, getNextReviewDate, calculateStreak } from './date';

describe('date utils', () => {
  describe('formatDate', () => {
    it('formats date in Russian locale', () => {
      const date = new Date('2025-01-09T12:00:00Z');
      expect(formatDate(date, 'ru')).toBe('9 января 2025');
    });

    it('formats date in short format', () => {
      const date = new Date('2025-01-09');
      expect(formatDate(date, 'ru', 'short')).toBe('09.01.2025');
    });
  });

  describe('calculateStreak', () => {
    it('returns 0 for empty activity', () => {
      expect(calculateStreak([])).toBe(0);
    });

    it('calculates consecutive days correctly', () => {
      const dates = [
        '2025-01-09',
        '2025-01-08',
        '2025-01-07',
        '2025-01-05'  // Gap
      ];
      expect(calculateStreak(dates)).toBe(3);
    });

    it('handles today correctly', () => {
      const today = new Date().toISOString().split('T')[0];
      expect(calculateStreak([today])).toBe(1);
    });
  });
});
```

**Пример тестирования custom hook:**
```typescript
// src/hooks/useCards.test.ts

import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCards } from './useCards';
import * as cardsApi from '@/api/endpoints/cards';

// Mock API
vi.mock('@/api/endpoints/cards');

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('useCards', () => {
  it('fetches cards successfully', async () => {
    const mockCards = [
      { id: '1', word: 'casa', translation: 'дом' },
      { id: '2', word: 'perro', translation: 'собака' },
    ];

    vi.mocked(cardsApi.getCards).mockResolvedValue(mockCards);

    const { result } = renderHook(() => useCards('deck-123'), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.cards).toEqual(mockCards);
  });

  it('handles error', async () => {
    vi.mocked(cardsApi.getCards).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useCards('deck-123'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});
```

#### Component Tests (React Testing Library)

**Принципы тестирования компонентов:**
- Тестировать как пользователь (не implementation details)
- Использовать semantic queries (getByRole, getByLabelText)
- Проверять accessibility
- Проверять user interactions

**Пример:**
```typescript
// src/components/ui/Button/Button.test.tsx

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { Button } from './Button';

describe('Button', () => {
  it('renders button with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();

    render(<Button onClick={handleClick}>Click me</Button>);

    await user.click(screen.getByRole('button'));

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Click me</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('shows loading state', () => {
    render(<Button loading>Click me</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('applies correct variant styles', () => {
    const { rerender } = render(<Button variant="primary">Primary</Button>);
    expect(screen.getByRole('button')).toHaveClass('button', 'button--primary');

    rerender(<Button variant="secondary">Secondary</Button>);
    expect(screen.getByRole('button')).toHaveClass('button', 'button--secondary');
  });
});
```

**Сложный компонент с interaction:**
```typescript
// src/components/flashcards/FlashCard/FlashCard.test.tsx

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { FlashCard } from './FlashCard';

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, onClick, ...props }: any) => (
      <div onClick={onClick} {...props}>
        {children}
      </div>
    ),
  },
}));

// Mock haptic hook
vi.mock('@/hooks/useHaptic', () => ({
  useHaptic: () => ({
    impactOccurred: vi.fn(),
  }),
}));

describe('FlashCard', () => {
  const defaultProps = {
    word: 'casa',
    translation: 'дом',
    example: 'Mi casa es tu casa',
    exampleTranslation: 'Мой дом - твой дом',
    onFlip: vi.fn(),
  };

  it('renders word on front side', () => {
    render(<FlashCard {...defaultProps} />);
    expect(screen.getByText('casa')).toBeInTheDocument();
    expect(screen.getByText(/Mi casa es tu casa/i)).toBeInTheDocument();
  });

  it('flips card on click', async () => {
    const user = userEvent.setup();
    const onFlip = vi.fn();

    render(<FlashCard {...defaultProps} onFlip={onFlip} />);

    await user.click(screen.getByText('casa'));

    expect(onFlip).toHaveBeenCalledTimes(1);
  });

  it('shows translation after flip', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<FlashCard {...defaultProps} />);

    await user.click(screen.getByText('casa'));

    // Simulate flip animation complete
    rerender(<FlashCard {...defaultProps} isFlipped />);

    expect(screen.getByText('дом')).toBeInTheDocument();
  });
});
```

#### Mocking API with MSW

```typescript
// tests/mocks/handlers.ts

import { http, HttpResponse } from 'msw';

export const handlers = [
  // Get cards
  http.get('/api/cards', ({ request }) => {
    const url = new URL(request.url);
    const deckId = url.searchParams.get('deck_id');

    return HttpResponse.json({
      data: [
        {
          id: '1',
          deck_id: deckId,
          word: 'casa',
          translation: 'дом',
          status: 'new',
        },
        {
          id: '2',
          deck_id: deckId,
          word: 'perro',
          translation: 'собака',
          status: 'learning',
        },
      ],
      pagination: {
        total: 2,
        limit: 20,
        offset: 0,
      },
    });
  }),

  // Create card
  http.post('/api/cards', async ({ request }) => {
    const body = await request.json();

    return HttpResponse.json(
      {
        created: body.words.map((word: string) => ({
          id: crypto.randomUUID(),
          word,
          translation: 'mock translation',
          status: 'new',
        })),
        duplicates: [],
        failed: [],
      },
      { status: 201 }
    );
  }),

  // Rate card
  http.post('/api/cards/rate', async ({ request }) => {
    const body = await request.json();

    return HttpResponse.json({
      id: body.card_id,
      interval_days: 3,
      next_review: new Date().toISOString(),
      status: 'review',
    });
  }),
];


// tests/setup.ts

import { setupServer } from 'msw/node';
import { handlers } from './mocks/handlers';
import { afterAll, afterEach, beforeAll } from 'vitest';

export const server = setupServer(...handlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

#### Test Coverage

**Запуск тестов:**
```bash
# Все тесты
npm test

# С coverage
npm test -- --coverage

# Watch mode
npm test -- --watch

# Конкретный файл
npm test Button.test.tsx
```

**Минимальное покрытие:**
- **Критичные компоненты: 100%**
  - Auth flow components
  - Payment components
  - CardStudySession
- **UI components: 90%**
- **Hooks: 90%**
- **Utils: 95%**
- **Overall: 75%**

---

### End-to-End Testing (Playwright - опционально)

**Тесты для критичных пользовательских сценариев:**

```typescript
// tests/e2e/card-study-flow.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Card Study Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock Telegram WebApp
    await page.addInitScript(() => {
      window.Telegram = {
        WebApp: {
          initData: 'mock_init_data',
          initDataUnsafe: { user: { id: 123456789 } },
          ready: () => {},
          expand: () => {},
        },
      };
    });

    await page.goto('/');
  });

  test('user can study flashcards', async ({ page }) => {
    // Navigate to cards
    await page.click('text=Практика');
    await page.click('text=Карточки');

    // Start study session
    await page.click('text=Начать изучение');

    // Flip card
    await page.click('[data-testid="flashcard"]');
    await expect(page.locator('text=дом')).toBeVisible();

    // Rate card
    await page.click('text=Знаю');

    // Verify next card loaded
    await expect(page.locator('[data-testid="flashcard"]')).toBeVisible();
  });

  test('user completes study session and sees stats', async ({ page }) => {
    await page.goto('/practice/cards/study');

    // Study 5 cards
    for (let i = 0; i < 5; i++) {
      await page.click('[data-testid="flashcard"]');
      await page.click('text=Знаю');
    }

    // Verify completion screen
    await expect(page.locator('text=Сессия завершена')).toBeVisible();
    await expect(page.locator('text=5 карточек изучено')).toBeVisible();
  });
});
```

---

## Code Review

### Процесс

**1. Pre-review (автор PR):**
- [ ] Self-review кода перед созданием PR
- [ ] Все тесты проходят локально
- [ ] Coverage ≥ 85% (backend) / 75% (frontend)
- [ ] Нет console.log / debugger
- [ ] Нет закомментированного кода
- [ ] Описание PR заполнено

**2. Automated checks (CI):**
- [ ] Линтеры проходят (ruff, eslint)
- [ ] Форматтеры проверены (black, prettier)
- [ ] Type checking (mypy, tsc)
- [ ] Все тесты проходят
- [ ] Coverage не упал

**3. Manual review (ревьюеры):**
- Минимум **2 approvals**
- Ревью в течение **24 часов** с момента создания PR
- Все комментарии должны быть **resolved** или обсуждены

**4. Merge:**
- Squash and merge (один коммит в main/develop)
- Автоматическое удаление feature branch

### Чеклист ревьюера

```markdown
## Architecture & Design
- [ ] Соответствие документации (`docs/`)
- [ ] Правильная layered architecture (handler → service → repository)
- [ ] Dependency Injection используется корректно
- [ ] Нет нарушений SOLID принципов
- [ ] Файлы < 300 строк (backend) / < 250 (frontend)
- [ ] Одна ответственность на класс/компонент

## Code Quality
- [ ] Код читаемый и понятный
- [ ] Нет дублирования (DRY)
- [ ] Имена переменных/функций ясные и описательные
- [ ] Нет магических чисел (используются константы)
- [ ] Правильная обработка ошибок
- [ ] Нет race conditions / memory leaks

## Security
- [ ] Валидация всех входных данных (Pydantic/Zod)
- [ ] Telegram initData валидируется через HMAC
- [ ] Authorization checks на endpoints
- [ ] Нет SQL injection / XSS уязвимостей
- [ ] Нет логирования паролей/токенов
- [ ] Rate limiting применяется где нужно

## Performance
- [ ] Нет N+1 запросов
- [ ] Используются индексы БД
- [ ] Async/await где возможно
- [ ] React: нет ненужных re-renders
- [ ] React: useMemo/useCallback где нужно
- [ ] Images оптимизированы

## Testing
- [ ] Coverage ≥ 85% (backend) / 75% (frontend)
- [ ] Unit tests для бизнес-логики
- [ ] Integration tests для API
- [ ] Тесты проверяют edge cases
- [ ] Тесты понятны и поддерживаемы
- [ ] Нет flaky tests

## Documentation
- [ ] Docstrings/JSDoc для публичных функций
- [ ] Комментарии объясняют "почему", не "что"
- [ ] README обновлен (если требуется)
- [ ] API документация обновлена
- [ ] Типы корректно описаны

## User Experience (Frontend)
- [ ] UI соответствует дизайну
- [ ] Анимации плавные
- [ ] Haptic feedback добавлен где нужно
- [ ] Loading states показываются
- [ ] Error messages понятны пользователю
- [ ] Accessibility (a11y) соблюдается
```

### Типы комментариев

**Используйте префиксы:**
- **`MUST:`** - критичная проблема, блокирует merge
- **`SHOULD:`** - важная рекомендация, стоит исправить
- **`CONSIDER:`** - предложение, можно обсудить
- **`NIT:`** - мелкое замечание, необязательно
- **`QUESTION:`** - вопрос для понимания

**Примеры:**
```
MUST: Нет валидации user_id из Telegram initData. Это критичная уязвимость безопасности.

SHOULD: Этот метод слишком большой (120 строк). Разбейте на подметоды для улучшения читаемости.

CONSIDER: Можно использовать useMemo здесь для оптимизации производительности?

NIT: Опечатка в комментарии: "recieve" → "receive"

QUESTION: Почему здесь используется setTimeout вместо async/await?
```

---

## Documentation

### Код

#### Backend (Python)

**Docstrings (Google Style):**
```python
def create_card(
    word: str,
    deck_id: UUID,
    profile_id: UUID,
    translation: Optional[str] = None
) -> Card:
    """
    Создать новую флеш-карточку со словом для изучения.

    Проверяет дубликаты по лемме слова, генерирует перевод через LLM
    если не указан, создает примеры использования.

    Args:
        word: Слово на изучаемом языке (например, "casa")
        deck_id: UUID колоды куда добавляется карточка
        profile_id: UUID языкового профиля пользователя
        translation: Перевод слова (опционально, будет сгенерирован если None)

    Returns:
        Card: Созданная карточка с заполненными полями:
            - word: исходное слово
            - translation: перевод
            - example: пример использования
            - example_translation: перевод примера
            - lemma: нормализованная форма слова
            - status: 'new'

    Raises:
        DuplicateCardError: Карточка с такой леммой уже существует в профиле
        LimitReachedError: Достигнут лимит карточек для free пользователя
        LLMServiceError: Ошибка при генерации контента через LLM

    Example:
        >>> service = FlashcardsService(card_repo, llm_service)
        >>> card = await service.create_card(
        ...     word="casa",
        ...     deck_id=deck.id,
        ...     profile_id=profile.id
        ... )
        >>> print(f"{card.word} - {card.translation}")
        casa - дом

    Note:
        Лемматизация выполняется через spaCy для определения базовой формы.
        Для испанского используется модель "es_core_news_sm".
    """
    pass
```

**Комментарии:**
```python
# ✅ Хорошие комментарии (объясняют "ПОЧЕМУ")

# Telegram может вернуть пустой user_id если подпись initData невалидна
# В этом случае мы не можем безопасно идентифицировать пользователя
if not user_id:
    raise AuthenticationError("Invalid initData")

# SM-2 алгоритм требует минимальный интервал 1 день
# даже при ответе "dont_know" для избежания спама карточками
new_interval = max(1, calculate_interval(rating))

# Используем Redis для кэширования активного профиля
# чтобы избежать дополнительного DB запроса на каждом API call
cached_profile = await redis.get(f"profile:active:{user_id}")


# ❌ Плохие комментарии (повторяют код)

# Проверяем что user_id существует
if not user_id:
    raise Error()

# Устанавливаем интервал в 1
interval = 1

# Получаем профиль из кэша
profile = cache.get(key)
```

#### Frontend (TypeScript)

**JSDoc:**
```typescript
/**
 * Хук для управления сессией изучения карточек.
 *
 * Управляет состоянием текущей карточки, прогрессом,
 * отправляет оценки на сервер и автоматически переходит к следующей.
 *
 * @param cards - Массив карточек для изучения
 * @returns Объект с текущей карточкой, методами управления и статистикой
 *
 * @example
 * ```tsx
 * const { currentCard, progress, rateCard, stats } = useCardStudySession(cards);
 *
 * return (
 *   <div>
 *     <FlashCard {...currentCard} />
 *     <CardRatingButtons onRate={rateCard} />
 *     <Progress value={progress} />
 *   </div>
 * );
 * ```
 */
export const useCardStudySession = (cards: Card[]) => {
  // ... implementation
};


/**
 * Валидирует и парсит Telegram initData.
 *
 * КРИТИЧНО: Эта функция проверяет HMAC подпись для защиты от подмены user_id.
 * Без этой валидации любой пользователь может выдать себя за другого.
 *
 * @param initData - Строка initData от Telegram WebApp API
 * @param botToken - Токен бота для верификации подписи
 * @returns Распарсенные и валидированные данные пользователя
 * @throws {AuthError} Если подпись невалидна или initData истек (>1 час)
 *
 * @see https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
 */
export const validateTelegramInitData = (
  initData: string,
  botToken: string
): TelegramUser => {
  // ... implementation
};
```

### Проект

#### README для модулей

**Каждый крупный модуль должен иметь README:**

```markdown
# Flashcards Service

Сервисный слой для работы с флеш-карточками.

## Ответственность

- Создание карточек с генерацией контента через LLM
- Управление интервальным повторением (SM-2 алгоритм)
- Проверка дубликатов по лемме
- Выбор следующей карточки для изучения

## Зависимости

- `CardRepository` - доступ к данным карточек
- `LLMService` - генерация переводов и примеров
- `UserService` - проверка лимитов пользователя

## API

### `create_card(word, deck_id, profile_id) -> Card`

Создает новую карточку.

**Параметры:**
- `word` - слово на изучаемом языке
- `deck_id` - ID колоды
- `profile_id` - ID языкового профиля

**Возвращает:** Созданную карточку

**Исключения:**
- `DuplicateCardError` - если карточка уже существует
- `LimitReachedError` - если достигнут лимит

**Пример:**
\`\`\`python
card = await service.create_card("casa", deck_id, profile_id)
\`\`\`

## Алгоритмы

### SM-2 (Spaced Repetition)

Реализован в `_calculate_next_interval()`.

**Логика:**
- `know` → интервал * 2.5
- `repeat` → интервал остается
- `dont_know` → интервал = 1 день

## Тестирование

Тесты находятся в `tests/unit/services/test_flashcards_service.py`

**Запуск:**
\`\`\`bash
pytest tests/unit/services/test_flashcards_service.py
\`\`\`

**Coverage:** 95%

## TODO

- [ ] Добавить поддержку кастомных алгоритмов повторения (альтернативы SM-2)
- [ ] Оптимизировать выбор следующей карточки (избегать слишком простых)
- [ ] Добавить A/B тестирование разных промптов для LLM
```

#### Обновление документации

**При изменениях ОБЯЗАТЕЛЬНО обновлять:**

1. **API изменения** → `backend-api.md`
2. **Архитектурные изменения** → `architecture.md`
3. **Новые компоненты UI** → `frontend-structure.md`, `frontend-screens.md`
4. **Изменение бизнес-логики** → соответствующий `backend-*.md`
5. **Новые use cases** → `use-cases.md`

**Процесс:**
- Документация обновляется **в том же PR** что и код
- Ревьюер проверяет соответствие документации
- Документация пишется **ДО кода** (TDD для docs)

---

## Performance

### Backend

#### Database Optimization

**Индексы:**
```python
# models/card.py

class Card(Base):
    __tablename__ = "cards"

    id = Column(UUID, primary_key=True)
    deck_id = Column(UUID, ForeignKey("decks.id"), nullable=False)
    profile_id = Column(UUID, ForeignKey("profiles.id"), nullable=False)
    lemma = Column(String(100), nullable=False)
    next_review = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Индексы для частых запросов
    __table_args__ = (
        Index('idx_deck_next_review', 'deck_id', 'next_review'),  # Для get_next_due_cards
        Index('idx_profile_lemma', 'profile_id', 'lemma', unique=True),  # Для check_duplicate
        Index('idx_created_at', 'created_at'),  # Для сортировки по дате
    )
```

**N+1 проблема:**
```python
# ❌ ПЛОХО - N+1 запросов
cards = await session.execute(select(Card).filter_by(deck_id=deck_id))
for card in cards.scalars():
    deck = await session.get(Deck, card.deck_id)  # N запросов!


# ✅ ХОРОШО - один запрос с join
stmt = (
    select(Card)
    .options(selectinload(Card.deck))  # Eager loading
    .filter(Card.deck_id == deck_id)
)
cards = await session.execute(stmt)
```

**Pagination:**
```python
# ✅ Всегда используйте limit/offset
stmt = (
    select(Card)
    .filter(Card.deck_id == deck_id)
    .order_by(Card.created_at.desc())
    .limit(20)
    .offset(offset)
)
```

#### Caching Strategy

**Redis для hot data:**
```python
# services/cache_service.py

class CacheService:
    """Сервис для кэширования."""

    async def get_active_profile(self, user_id: UUID) -> Optional[LanguageProfile]:
        """Получить активный профиль из кэша."""
        key = f"profile:active:{user_id}"
        cached = await redis.get(key)

        if cached:
            return LanguageProfile.parse_raw(cached)

        # Cache miss - fetch from DB
        profile = await profile_repo.get_active(user_id)

        if profile:
            await redis.setex(
                key,
                3600,  # TTL 1 hour
                profile.json()
            )

        return profile

    async def invalidate_active_profile(self, user_id: UUID) -> None:
        """Инвалидировать кэш активного профиля."""
        await redis.delete(f"profile:active:{user_id}")
```

**Что кэшировать:**
- Активный профиль пользователя (TTL: 1 час)
- User stats (TTL: 5 минут)
- LLM ответы для одинаковых промптов (TTL: 24 часа)
- Rate limit counters (TTL: 24 часа)

#### Async Operations

**Используйте async/await:**
```python
# ✅ Параллельные операции
async def create_multiple_cards(words: List[str], deck_id: UUID):
    # Генерируем контент для всех слов параллельно
    tasks = [
        llm_service.generate_card_content(word, language, level)
        for word in words
    ]
    contents = await asyncio.gather(*tasks)

    # Сохраняем в БД batch
    cards = [
        Card(word=word, **content)
        for word, content in zip(words, contents)
    ]
    await card_repo.create_many(cards)
```

### Frontend

#### Code Splitting

**Lazy load routes:**
```typescript
// router/routes.tsx

import { lazy } from 'react';

export const routes = [
  {
    path: '/',
    element: <HomePage />,  // Eager (critical)
  },
  {
    path: '/practice/cards',
    element: lazy(() => import('@/pages/Practice/Cards/CardsPage')),  // Lazy
  },
  {
    path: '/practice/exercises',
    element: lazy(() => import('@/pages/Practice/Exercises/ExercisesPage')),
  },
  {
    path: '/groups',
    element: lazy(() => import('@/pages/Groups/GroupsPage')),
  },
];
```

**Dynamic imports:**
```typescript
// Only load when needed
const handleExportData = async () => {
  const { exportToCSV } = await import('@/utils/export');
  exportToCSV(data);
};
```

#### React Performance

**Мемоизация:**
```typescript
// ✅ useMemo для дорогих вычислений
const sortedCards = useMemo(
  () => cards.sort((a, b) => a.next_review - b.next_review),
  [cards]
);

// ✅ useCallback для функций в пропсах
const handleRateCard = useCallback(
  (cardId: string, rating: CardRating) => {
    rateCardMutation.mutate({ cardId, rating });
  },
  [rateCardMutation]
);

// ✅ memo для компонентов
export const CardItem = memo<CardItemProps>(({ card, onSelect }) => {
  return <div onClick={() => onSelect(card.id)}>{card.word}</div>;
});
```

**Избегать ненужных re-renders:**
```typescript
// ❌ ПЛОХО - создается новый объект на каждом рендере
<FlashCard
  onFlip={() => handleFlip(card.id)}  // Новая функция каждый раз
  style={{ padding: 16 }}  // Новый объект каждый раз
/>


// ✅ ХОРОШО - стабильные ссылки
const handleFlip = useCallback(() => handleFlip(card.id), [card.id]);
const cardStyle = useMemo(() => ({ padding: 16 }), []);

<FlashCard onFlip={handleFlip} style={cardStyle} />
```

#### Image Optimization

**WebP format:**
```typescript
<img
  src="/images/hero.webp"
  srcSet="/images/hero-sm.webp 400w, /images/hero-md.webp 800w, /images/hero-lg.webp 1200w"
  sizes="(max-width: 400px) 400px, (max-width: 800px) 800px, 1200px"
  alt="Hero"
  loading="lazy"
/>
```

**SVG для icons:**
```typescript
// Используйте SVG вместо PNG для иконок
import { ReactComponent as CardIcon } from '@/assets/icons/card.svg';

<CardIcon width={24} height={24} />
```

---

## Security Best Practices

### Authentication

**Telegram initData validation:**
```python
# app/core/auth.py

import hmac
import hashlib
import time
from urllib.parse import parse_qsl

def validate_telegram_initdata(init_data: str, bot_token: str) -> dict:
    """
    Валидировать Telegram initData через HMAC-SHA256.

    КРИТИЧНО: Это единственный способ безопасно получить user_id.
    """
    # 1. Parse query string
    params = dict(parse_qsl(init_data))

    # 2. Extract hash
    received_hash = params.pop('hash', None)
    if not received_hash:
        raise AuthenticationError("Missing hash in initData")

    # 3. Check timestamp (< 1 hour old)
    auth_date = int(params.get('auth_date', 0))
    if time.time() - auth_date > 3600:
        raise AuthenticationError("initData expired")

    # 4. Calculate expected hash
    data_check_string = '\n'.join(
        f"{key}={value}"
        for key, value in sorted(params.items())
    )

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256
    ).digest()

    expected_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    # 5. Compare hashes (constant-time)
    if not hmac.compare_digest(expected_hash, received_hash):
        raise AuthenticationError("Invalid hash - possible tampering")

    # 6. Extract user data
    user_data = json.loads(params['user'])
    return user_data
```

**Authorization checks:**
```python
# ❌ ПЛОХО - нет проверки ownership
@router.delete("/cards/{card_id}")
async def delete_card(card_id: UUID):
    await card_repo.delete(card_id)


# ✅ ХОРОШО - проверка что пользователь владеет ресурсом
@router.delete("/cards/{card_id}")
async def delete_card(
    card_id: UUID,
    current_user: User = Depends(get_current_user),
    card_repo: CardRepository = Depends()
):
    card = await card_repo.get(card_id)

    if not card:
        raise HTTPException(404, "Card not found")

    # Проверка что карточка принадлежит пользователю
    deck = await deck_repo.get(card.deck_id)
    if deck.profile.user_id != current_user.id:
        raise HTTPException(403, "Forbidden")

    await card_repo.delete(card_id)
```

### Input Validation

**Pydantic models:**
```python
from pydantic import BaseModel, Field, validator

class CreateCardRequest(BaseModel):
    """Request для создания карточки."""

    word: str = Field(..., min_length=1, max_length=100)
    deck_id: UUID
    profile_id: UUID
    translation: Optional[str] = Field(None, max_length=200)

    @validator('word')
    def word_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Word cannot be empty')
        return v.strip()

    @validator('translation')
    def translation_safe(cls, v):
        if v and ('<script>' in v.lower() or 'javascript:' in v.lower()):
            raise ValueError('Invalid translation content')
        return v
```

**SQL Injection protection:**
```python
# ✅ Всегда используйте ORM или параметризованные запросы
# SQLAlchemy защищает автоматически

stmt = select(Card).where(Card.word == word)  # ✅ Safe

# ❌ НИКОГДА не используйте string interpolation
query = f"SELECT * FROM cards WHERE word = '{word}'"  # ❌ SQL injection!
```

### Environment Variables

**Никогда не храните secrets в коде:**
```python
# ❌ ПЛОХО
OPENAI_API_KEY = "sk-..."


# ✅ ХОРОШО
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""

    OPENAI_API_KEY: str
    STRIPE_SECRET_KEY: str
    DATABASE_URL: str
    REDIS_URL: str

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

**.env.example:**
```bash
# OpenAI
OPENAI_API_KEY=sk-your-key-here

# Stripe
STRIPE_SECRET_KEY=sk_test_your-key-here
STRIPE_WEBHOOK_SECRET=whsec_your-secret-here

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/lang_agent

# Redis
REDIS_URL=redis://localhost:6379/0

# Telegram
BOT_TOKEN=123456:ABC-DEF...
WEBHOOK_SECRET=your-webhook-secret
```

### Rate Limiting

**Защита от DDoS:**
```python
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/cards")
@limiter.limit("10/minute")  # 10 запросов в минуту
async def create_card(request: Request, ...):
    pass


# Per-user limits
@router.post("/exercises/generate")
async def generate_exercise(
    current_user: User = Depends(get_current_user),
    limit_service: LimitService = Depends()
):
    # Проверка дневного лимита
    if not await limit_service.check_limit(current_user.id, "exercises"):
        raise HTTPException(
            status_code=429,
            detail="Daily exercise limit reached"
        )

    # ... generate exercise
```

### Logging

**Безопасное логирование:**
```python
import logging

logger = logging.getLogger(__name__)

# ❌ ПЛОХО - логируем чувствительные данные
logger.info(f"User {user_id} with token {jwt_token} logged in")
logger.debug(f"Stripe payment: {stripe_response}")


# ✅ ХОРОШО - только необходимая информация
logger.info(f"User {user_id} logged in", extra={"user_id": user_id})
logger.info("Payment processed", extra={
    "user_id": user_id,
    "amount": amount,
    "currency": currency
})
```

---

## Перед завершением разработки

### Final Checklist

**Перед тем как считать задачу выполненной:**

1. **✅ Все тесты проходят**
   ```bash
   # Backend
   pytest --cov=app --cov-fail-under=85

   # Frontend
   npm test -- --coverage --run
   ```

2. **✅ Coverage достигнут**
   - Backend: ≥85% (критичные модули 100%)
   - Frontend: ≥75% (критичные компоненты 100%)

3. **✅ Линтеры проходят**
   ```bash
   # Backend
   ruff check backend/
   black --check backend/
   mypy backend/

   # Frontend
   npm run lint
   npm run typecheck
   ```

4. **✅ Документация обновлена**
   - [ ] Обновлены релевантные файлы в `docs/`
   - [ ] Добавлены/обновлены docstrings/JSDoc
   - [ ] README обновлен если требуется

5. **✅ Код соответствует guidelines**
   - [ ] Файлы < 300/250 строк
   - [ ] Одна ответственность на класс/компонент
   - [ ] Нет дублирования
   - [ ] Нет TODO без Issue ID

6. **✅ Security review**
   - [ ] Нет hardcoded secrets
   - [ ] Валидация всех входных данных
   - [ ] Authorization checks на endpoints
   - [ ] Нет SQL injection / XSS уязвимостей

7. **✅ Performance check**
   - [ ] Нет N+1 запросов
   - [ ] Используются индексы БД
   - [ ] Нет memory leaks
   - [ ] Bundle size < 200KB (initial load)

8. **✅ Manual testing**
   - [ ] Проверено на разных устройствах/браузерах
   - [ ] Happy path работает
   - [ ] Error cases обрабатываются корректно
   - [ ] UI/UX соответствует ожиданиям

9. **✅ CI/CD готово**
   - [ ] GitHub Actions проходит
   - [ ] Docker build успешен (если применимо)
   - [ ] Environment variables настроены

10. **✅ Rollback plan**
    - [ ] Понятно как откатить изменения
    - [ ] Database migrations обратимы
    - [ ] Feature flags используются для больших изменений

### Запуск полного набора тестов

**Backend:**
```bash
# 1. Unit tests
pytest tests/unit/ -v --cov=app/services --cov=app/utils --cov-report=term

# 2. Integration tests
pytest tests/integration/ -v --cov=app --cov-append

# 3. Full coverage report
pytest --cov=app --cov-report=html --cov-report=term --cov-fail-under=85

# 4. Type checking
mypy app/

# 5. Linting
ruff check app/
black --check app/
```

**Frontend:**
```bash
# 1. Unit tests
npm test -- --coverage --run

# 2. Type checking
npm run typecheck

# 3. Linting
npm run lint

# 4. Build test
npm run build

# 5. E2E tests (опционально)
npm run test:e2e
```

### Deployment Checklist

**Перед деплоем в production:**

1. **✅ Все тесты проходят в CI/CD**
2. **✅ Staging протестирован**
3. **✅ Database migrations применены на staging**
4. **✅ Monitoring alerts настроены**
5. **✅ Rollback plan документирован**
6. **✅ Feature flags готовы (для больших изменений)**
7. **✅ Performance testing пройден**
8. **✅ Security audit пройден**
9. **✅ Documentation обновлена**
10. **✅ Stakeholders информированы**

---

## Summary

**Ключевые принципы:**

1. **📚 Документация - источник истины**
   - Код следует документации
   - Любое отклонение согласовывается

2. **✅ Тестирование обязательно**
   - 85% coverage (backend), 75% (frontend)
   - 100% для критичных модулей
   - Проверка тестов перед каждым коммитом

3. **📏 Малые, focused файлы**
   - Backend: < 300 строк
   - Frontend: < 250 строк
   - Одна ответственность на класс/компонент

4. **📝 Документация кода**
   - Docstrings/JSDoc для всех публичных API
   - Комментарии объясняют "почему", не "что"
   - README для каждого модуля

5. **🔒 Безопасность всегда**
   - Валидация Telegram initData
   - Authorization checks
   - Нет secrets в коде
   - Input validation

6. **⚡ Производительность важна**
   - Нет N+1 запросов
   - Кэширование hot data
   - Code splitting
   - Async где возможно

7. **👥 Code Review обязателен**
   - Минимум 2 approvals
   - Все комментарии resolved
   - CI проходит

8. **🚀 Перед завершением: тесты!**
   - Все тесты проходят
   - Coverage достигнут
   - Линтеры проходят
   - Документация обновлена

**Помните:** Качество кода = качество продукта. Уделяйте время на правильную архитектуру, тестирование и документацию с самого начала.
