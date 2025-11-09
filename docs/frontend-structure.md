# Структура Frontend (React Mini App)

## Технологический стек

### Основа

**Core:**
- **React** 18.2+ (с Hooks, Suspense, Concurrent Mode)
- **TypeScript** 5.0+ (strict mode)
- **Vite** 4+ (для быстрой сборки)

**Telegram Integration:**
- **@twa-dev/sdk** 7+ (официальный Telegram Mini App SDK)
- **@twa-dev/types** (TypeScript типы для Telegram WebApp API)

### UI библиотека

**Подход: Custom UI компоненты**

Причины:
- Полный контроль над дизайном (закатная тема)
- Минимальный bundle size
- Оптимизация для Telegram Mini App
- Нет лишних компонентов

**Вспомогательные библиотеки:**
- **Headless UI** (@headlessui/react) - для accessible компонентов без стилей
- **Radix UI Primitives** (@radix-ui/react-*) - для сложных компонентов (Dialog, Select, Tabs)
- **Framer Motion** 10+ - для анимаций
- **React Spring** - для физических анимаций (spring, drag)

### Styling

**CSS:**
- **CSS Modules** (для scoped стилей)
- **PostCSS** с plugins:
  - autoprefixer
  - postcss-nested
  - postcss-custom-media (для responsive breakpoints)

**Альтернатива:** Tailwind CSS (если команда предпочитает utility-first)

**Design tokens:**
```typescript
// src/styles/tokens.ts
export const colors = {
  background: {
    primary: '#0A0E27',
    secondary: '#1A1D35',
    surface: '#252941'
  },
  accent: {
    sunset: '#FF6B35',
    coral: '#FF8C5A',
    pink: '#FF5E78',
    purple: '#B565E8'
  },
  // ...
};
```

### State Management

**Комбинированный подход:**

1. **React Query** (@tanstack/react-query) 4+ - для server state
   - Кэширование API данных
   - Автоматическая revalidation
   - Optimistic updates
   - Prefetching

2. **Zustand** 4+ - для client state
   - Легковесная альтернатива Redux
   - TypeScript-friendly
   - Middleware для persistence

3. **React Context** - для простых случаев
   - Theme context
   - Auth context
   - Active profile context

**Почему не Redux:**
- Излишняя сложность для Mini App
- Больший bundle size
- React Query + Zustand покрывают все потребности

### Routing

**React Router** 6+

**Конфигурация:**
```typescript
// src/router/index.tsx
const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    errorElement: <ErrorBoundary />,
    children: [
      { index: true, element: <HomePage /> },
      {
        path: 'practice',
        element: <PracticeLayout />,
        children: [
          { path: 'cards', element: <CardsPage /> },
          { path: 'cards/study', element: <CardStudyPage /> },
          // ...
        ]
      },
      // ...
    ]
  },
  { path: '/onboarding', element: <OnboardingFlow /> }
]);
```

**Navigation Guards:**
```typescript
// src/router/guards.tsx
export const AuthGuard: FC<PropsWithChildren> = ({ children }) => {
  const isAuthenticated = useTelegramAuth();
  return isAuthenticated ? children : <Navigate to="/error" />;
};
```

### API клиент

**Axios** 1.4+ с кастомными interceptors

**Структура:**
```typescript
// src/api/client.ts
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000
});

// Interceptors для auth, error handling, logging
apiClient.interceptors.request.use(/* Telegram initData */);
apiClient.interceptors.response.use(/* error handling */);
```

**Альтернатива для простых случаев:**
- **ky** (современная альтернатива fetch)
- Или нативный **fetch** с wrapper

**React Query integration:**
```typescript
// src/api/hooks/useCards.ts
export const useCards = (deckId: string) => {
  return useQuery({
    queryKey: ['cards', deckId],
    queryFn: () => cardsApi.getCards(deckId),
    staleTime: 2 * 60 * 1000
  });
};
```

### Тестирование

**Unit & Integration:**
- **Vitest** (совместим с Vite, быстрее Jest)
- **React Testing Library**
- **MSW** (Mock Service Worker) - для мокирования API

**E2E:**
- **Playwright** (опционально, для критичных флоу)

### Форматирование и линтинг

**Code Quality:**
- **ESLint** 8+ с конфигами:
  - eslint-config-airbnb-typescript
  - eslint-plugin-react-hooks
  - eslint-plugin-jsx-a11y
- **Prettier** 3+
- **Husky** + **lint-staged** (pre-commit hooks)

**TypeScript:**
```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

### Дополнительные библиотеки

**Utilities:**
- **date-fns** 2+ (работа с датами, легче moment.js)
- **zod** 3+ (валидация схем, runtime type checking)
- **clsx** + **tailwind-merge** (условные классы)

**Charts (для статистики):**
- **Recharts** 2+ (declarative charts для React)
- Альтернатива: **visx** (более низкоуровневая, от Airbnb)

**Animations:**
- **Framer Motion** (декларативные анимации)
- **React Spring** (физические анимации)
- **@use-gesture/react** (gesture handling)

**i18n (для будущих версий):**
- **react-i18next** (когда понадобятся переводы интерфейса)

---

## Структура проекта

```
telegram-lang-mini-app/
├── public/
│   ├── icons/              # App icons
│   ├── illustrations/      # Empty states, onboarding
│   └── favicon.ico
│
├── src/
│   ├── api/                # API layer
│   │   ├── client.ts       # Axios instance
│   │   ├── endpoints/      # API endpoints
│   │   │   ├── cards.ts
│   │   │   ├── exercises.ts
│   │   │   ├── groups.ts
│   │   │   ├── profiles.ts
│   │   │   └── users.ts
│   │   └── hooks/          # React Query hooks
│   │       ├── useCards.ts
│   │       ├── useExercises.ts
│   │       └── ...
│   │
│   ├── assets/             # Static assets
│   │   ├── fonts/
│   │   ├── images/
│   │   └── lottie/         # Lottie animations
│   │
│   ├── components/         # Reusable components
│   │   ├── ui/             # Basic UI components
│   │   │   ├── Button/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Button.module.css
│   │   │   │   └── index.ts
│   │   │   ├── Card/
│   │   │   ├── Input/
│   │   │   ├── Modal/
│   │   │   ├── Badge/
│   │   │   ├── Progress/
│   │   │   ├── Tabs/
│   │   │   ├── Toast/
│   │   │   └── Skeleton/
│   │   │
│   │   ├── layout/         # Layout components
│   │   │   ├── Header/
│   │   │   ├── BottomNav/
│   │   │   ├── RootLayout/
│   │   │   └── PracticeLayout/
│   │   │
│   │   ├── flashcards/     # Flashcard components
│   │   │   ├── FlashCard/
│   │   │   ├── CardList/
│   │   │   ├── DeckCard/
│   │   │   └── CardStudySession/
│   │   │
│   │   ├── exercises/      # Exercise components
│   │   │   ├── ExerciseCard/
│   │   │   ├── FreeTextExercise/
│   │   │   ├── MultipleChoiceExercise/
│   │   │   └── ExerciseSession/
│   │   │
│   │   ├── groups/         # Group components
│   │   │   ├── GroupCard/
│   │   │   ├── MemberList/
│   │   │   └── InviteModal/
│   │   │
│   │   ├── profile/        # Profile components
│   │   │   ├── ProfileCard/
│   │   │   ├── LanguageProfileCard/
│   │   │   └── StatsCard/
│   │   │
│   │   └── shared/         # Shared components
│   │       ├── EmptyState/
│   │       ├── ErrorBoundary/
│   │       ├── Loader/
│   │       └── ConfirmDialog/
│   │
│   ├── features/           # Feature-specific logic
│   │   ├── auth/
│   │   │   ├── hooks/
│   │   │   ├── utils/
│   │   │   └── types.ts
│   │   ├── onboarding/
│   │   ├── cards/
│   │   ├── exercises/
│   │   └── subscription/
│   │
│   ├── hooks/              # Custom React hooks
│   │   ├── useTelegram.ts
│   │   ├── useHaptic.ts
│   │   ├── useBackButton.ts
│   │   ├── useScrollPosition.ts
│   │   ├── useDebounce.ts
│   │   └── useLocalStorage.ts
│   │
│   ├── pages/              # Page components
│   │   ├── Home/
│   │   │   ├── HomePage.tsx
│   │   │   └── HomePage.module.css
│   │   ├── Onboarding/
│   │   │   ├── steps/
│   │   │   └── OnboardingFlow.tsx
│   │   ├── Practice/
│   │   │   ├── Cards/
│   │   │   │   ├── CardsPage.tsx
│   │   │   │   ├── CardStudyPage.tsx
│   │   │   │   ├── DeckDetailsPage.tsx
│   │   │   │   └── AddCardPage.tsx
│   │   │   └── Exercises/
│   │   │       ├── ExercisesPage.tsx
│   │   │       ├── ExerciseSessionPage.tsx
│   │   │       └── TopicDetailsPage.tsx
│   │   ├── Groups/
│   │   │   ├── GroupsPage.tsx
│   │   │   ├── GroupDetailsPage.tsx
│   │   │   └── CreateGroupPage.tsx
│   │   ├── Profile/
│   │   │   ├── ProfilePage.tsx
│   │   │   ├── StatsPage.tsx
│   │   │   ├── SettingsPage.tsx
│   │   │   └── SubscriptionPage.tsx
│   │   ├── Error/
│   │   │   ├── ErrorPage.tsx
│   │   │   └── NotFoundPage.tsx
│   │   └── Premium/
│   │       └── PremiumPage.tsx
│   │
│   ├── router/             # Routing configuration
│   │   ├── index.tsx
│   │   ├── guards.tsx
│   │   └── routes.tsx
│   │
│   ├── store/              # State management (Zustand)
│   │   ├── slices/
│   │   │   ├── authSlice.ts
│   │   │   ├── profileSlice.ts
│   │   │   ├── uiSlice.ts
│   │   │   └── settingsSlice.ts
│   │   ├── middleware/
│   │   │   └── persistMiddleware.ts
│   │   └── index.ts
│   │
│   ├── styles/             # Global styles
│   │   ├── globals.css
│   │   ├── tokens.ts       # Design tokens
│   │   ├── animations.css
│   │   └── variables.css
│   │
│   ├── types/              # TypeScript types
│   │   ├── api.ts          # API types
│   │   ├── models.ts       # Domain models
│   │   ├── telegram.ts     # Telegram types
│   │   └── common.ts       # Common types
│   │
│   ├── utils/              # Utility functions
│   │   ├── api.ts
│   │   ├── date.ts
│   │   ├── format.ts
│   │   ├── storage.ts
│   │   ├── validation.ts
│   │   └── telegram.ts
│   │
│   ├── constants/          # Constants
│   │   ├── languages.ts
│   │   ├── routes.ts
│   │   └── config.ts
│   │
│   ├── App.tsx             # Root component
│   ├── main.tsx            # Entry point
│   └── vite-env.d.ts
│
├── .env.example            # Environment variables template
├── .env.development
├── .env.production
├── .eslintrc.json
├── .prettierrc
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── package.json
└── README.md
```

---

## Компоненты

### UI компоненты (Design System)

#### 1. Button

**Variants:**
- Primary (gradient background)
- Secondary (gradient border, transparent)
- Ghost (no border, colored text)

**Props:**
```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
  disabled?: boolean;
  loading?: boolean;
  icon?: ReactNode;
  onClick?: () => void;
  children: ReactNode;
}
```

**Usage:**
```tsx
<Button variant="primary" icon={<Plus />} onClick={handleAdd}>
  Добавить карточку
</Button>
```

---

#### 2. Card

**Surface component для карточек**

**Props:**
```typescript
interface CardProps {
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hoverable?: boolean;
  onClick?: () => void;
  gradient?: boolean; // для gradient border/background
  className?: string;
  children: ReactNode;
}
```

**Styles:**
- Background: `#252941`
- Border radius: 20px
- Shadow: `0 4px 24px rgba(0, 0, 0, 0.3)`
- Hover: gradient glow

---

#### 3. Input / Textarea

**Form inputs**

**Props:**
```typescript
interface InputProps {
  label?: string;
  placeholder?: string;
  error?: string;
  disabled?: boolean;
  type?: 'text' | 'email' | 'password';
  icon?: ReactNode;
  value: string;
  onChange: (value: string) => void;
}
```

**Styles:**
- Background: `#1A1D35`
- Border: 1px solid `#3A3D55`
- Focus: gradient border (2px)
- Height: 48px

---

#### 4. Modal / BottomSheet

**Modal dialogs**

**Types:**
- Alert (center modal)
- BottomSheet (slides from bottom)
- FullScreen (covers entire screen)

**Props:**
```typescript
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  type?: 'alert' | 'bottomSheet' | 'fullScreen';
  size?: 'sm' | 'md' | 'lg' | 'auto';
  children: ReactNode;
}
```

**Features:**
- Backdrop (rgba(0,0,0,0.6))
- Drag handle для bottom sheets
- Swipe to dismiss
- Focus trap
- Escape to close

---

#### 5. Badge

**Status indicators**

**Variants:**
- Default (gradient border)
- Success (green)
- Error (red)
- Warning (yellow)
- Info (blue)

**Props:**
```typescript
interface BadgeProps {
  variant?: 'default' | 'success' | 'error' | 'warning' | 'info';
  size?: 'sm' | 'md';
  children: ReactNode;
}
```

---

#### 6. Progress

**Progress indicators**

**Types:**
- Linear (progress bar)
- Circular (spinner)
- Ring (circular progress)

**Props:**
```typescript
interface ProgressProps {
  value?: number; // 0-100
  type?: 'linear' | 'circular' | 'ring';
  size?: 'sm' | 'md' | 'lg';
  color?: 'gradient' | 'success' | 'error';
}
```

---

#### 7. Tabs / SegmentedControl

**Tab navigation**

**Props:**
```typescript
interface TabsProps {
  tabs: Array<{
    id: string;
    label: string;
    icon?: ReactNode;
  }>;
  activeTab: string;
  onChange: (tabId: string) => void;
}
```

**Styles:**
- Full width
- Active: gradient background
- Smooth transition (250ms)

---

#### 8. Toast

**Notifications**

**Props:**
```typescript
interface ToastProps {
  type: 'success' | 'error' | 'info';
  message: string;
  duration?: number; // ms
  position?: 'top' | 'bottom';
}
```

**API:**
```typescript
toast.success('Карточка добавлена');
toast.error('Ошибка сети');
```

---

#### 9. Skeleton

**Loading placeholders**

**Props:**
```typescript
interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  variant?: 'text' | 'rect' | 'circle';
  animation?: 'pulse' | 'wave';
}
```

---

#### 10. EmptyState

**Empty states**

**Props:**
```typescript
interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}
```

---

### Компоненты карточек (Flashcards)

#### 1. FlashCard

**Флипающаяся карточка**

**Props:**
```typescript
interface FlashCardProps {
  word: string;
  translation: string;
  example: string;
  exampleTranslation: string;
  side: 'front' | 'back'; // какая сторона показана
  language: 'learning' | 'native'; // какой язык на front
  onFlip: () => void;
}
```

**Features:**
- 3D flip animation (rotateY)
- Tap to flip
- Gradient glow on hover
- Responsive font sizes

**Component structure:**
```tsx
<div className="flashcard-container">
  <motion.div
    className="flashcard"
    animate={{ rotateY: isFlipped ? 180 : 0 }}
  >
    <div className="flashcard-front">
      <h2>{word}</h2>
      <p>{example}</p>
    </div>
    <div className="flashcard-back">
      <h3>{translation}</h3>
      <p>{exampleTranslation}</p>
    </div>
  </motion.div>
</div>
```

---

#### 2. CardRatingButtons

**Кнопки оценки (Знаю/Повторить/Не знаю)**

**Props:**
```typescript
interface CardRatingButtonsProps {
  onRate: (rating: 'know' | 'repeat' | 'dontKnow') => void;
  disabled?: boolean;
}
```

**Layout:**
- 3 кнопки в ряд
- Gap: 12px
- Height: 56px
- Градиентные цвета (красный, желтый, зеленый)

---

#### 3. DeckCard

**Карточка колоды в списке**

**Props:**
```typescript
interface DeckCardProps {
  deck: {
    id: string;
    name: string;
    cardsCount: number;
    todayCount: number;
    isActive: boolean;
    isGroup: boolean;
    ownerName?: string;
  };
  onClick: () => void;
}
```

**Visual:**
- Icon папки (градиент)
- Название
- Статистика ("45 карточек • 12 на сегодня")
- Badge "Активна" (если активная)
- Badge "👥 от [имя]" (если групповая)

---

#### 4. CardList

**Список карточек**

**Props:**
```typescript
interface CardListProps {
  cards: Card[];
  onCardClick: (cardId: string) => void;
  searchQuery?: string;
}
```

**Features:**
- Search bar
- Virtual scrolling (для больших списков)
- Pull to refresh

---

#### 5. CardStudySession

**Компонент сессии изучения**

**Props:**
```typescript
interface CardStudySessionProps {
  deckId: string;
  cards: Card[];
  onComplete: (stats: SessionStats) => void;
  onExit: () => void;
}
```

**State:**
```typescript
{
  currentIndex: number;
  isFlipped: boolean;
  progress: number;
  stats: {
    know: number;
    repeat: number;
    dontKnow: number;
  }
}
```

---

### Компоненты упражнений (Exercises)

#### 1. FreeTextExercise

**Упражнение со свободным вводом**

**Props:**
```typescript
interface FreeTextExerciseProps {
  question: string;
  prompt: string;
  onSubmit: (answer: string) => void;
  onHint?: () => void;
}
```

**Layout:**
- Вопрос (heading)
- Prompt (body large, gradient text)
- Textarea для ответа
- Кнопки: "Подсказка" (ghost) + "Проверить" (primary)

---

#### 2. MultipleChoiceExercise

**Упражнение с выбором варианта**

**Props:**
```typescript
interface MultipleChoiceExerciseProps {
  question: string;
  options: string[];
  correctIndex: number;
  onSelect: (index: number) => void;
}
```

**State:**
- selected: number | null
- showResult: boolean

**Visual:**
- 4 варианта (вертикально)
- Выбранный: gradient border
- После проверки:
  - Правильный: зеленая заливка + ✓
  - Неправильный: красная заливка + ❌

---

#### 3. ExerciseFeedback

**Компонент обратной связи**

**Props:**
```typescript
interface ExerciseFeedbackProps {
  result: 'correct' | 'partial' | 'incorrect';
  correctAnswer: string;
  explanation: string;
  onContinue: () => void;
}
```

**Visual:**
- Icon (✓ / ⚠ / ❌)
- Result text
- Правильный ответ
- Объяснение
- Кнопка "Продолжить"

---

#### 4. TopicCard

**Карточка темы в списке**

**Props:**
```typescript
interface TopicCardProps {
  topic: {
    id: string;
    name: string;
    description: string;
    type: 'grammar' | 'vocabulary' | 'situation';
    exercisesCount: number;
    accuracy: number;
    isActive: boolean;
    isGroup: boolean;
    ownerName?: string;
  };
  onClick: () => void;
}
```

---

#### 5. ExerciseSession

**Компонент сессии упражнений**

**Props:**
```typescript
interface ExerciseSessionProps {
  topicId: string;
  count: number; // количество упражнений в сессии
  onComplete: (stats: SessionStats) => void;
  onExit: () => void;
}
```

**Flow:**
1. Получить упражнения от API
2. Показать упражнение
3. Получить ответ
4. Показать feedback
5. Next exercise
6. Complete → stats screen

---

### Навигационные компоненты

#### 1. BottomNav

**Основная навигация**

**Props:**
```typescript
interface BottomNavProps {
  activeRoute: string;
  notificationCount: number;
}
```

**Items:**
- Home, Practice, Groups, Profile
- Icons + labels
- Active state (gradient)
- Tap animation

---

#### 2. Header

**Top bar**

**Variants:**
- Default (title + actions)
- WithBackButton (back + title + actions)
- Search (search bar)
- Minimal (только back button)

**Props:**
```typescript
interface HeaderProps {
  title?: string;
  showBack?: boolean;
  onBack?: () => void;
  actions?: ReactNode;
}
```

---

#### 3. TabBar

**Tab navigation within pages**

**Props:**
```typescript
interface TabBarProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (tabId: string) => void;
}
```

---

### Layout компоненты

#### 1. RootLayout

**Корневой layout**

**Features:**
- BottomNav (если не скрыт)
- Toast container
- Modal root
- Error boundary

---

#### 2. PracticeLayout

**Layout для режимов практики**

**Features:**
- Нет BottomNav
- Minimal header
- Full screen content

---

#### 3. OnboardingLayout

**Layout для онбординга**

**Features:**
- Progress indicator
- Back/Next buttons
- No BottomNav

---

### Shared компоненты

#### 1. ConfirmDialog

**Диалог подтверждения**

**Props:**
```typescript
interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}
```

---

#### 2. LoadingScreen

**Full screen loader**

**Props:**
```typescript
interface LoadingScreenProps {
  message?: string;
}
```

---

#### 3. ErrorBoundary

**Error boundary wrapper**

**Props:**
```typescript
interface ErrorBoundaryProps {
  fallback?: ReactNode;
  onError?: (error: Error) => void;
  children: ReactNode;
}
```

---

## Интеграция с Telegram

### Telegram WebApp API

#### Инициализация

```typescript
// src/utils/telegram.ts
import { WebApp } from '@twa-dev/sdk';

export const initTelegramApp = () => {
  // Расширить WebApp на весь экран
  WebApp.expand();

  // Включить closing confirmation
  WebApp.enableClosingConfirmation();

  // Установить header color
  WebApp.setHeaderColor('#0A0E27');

  // Установить background color
  WebApp.setBackgroundColor('#0A0E27');

  // Готов к использованию
  WebApp.ready();
};
```

#### Custom Hook

```typescript
// src/hooks/useTelegram.ts
import { useEffect, useState } from 'react';
import { WebApp } from '@twa-dev/sdk';

export const useTelegram = () => {
  const [webApp] = useState(WebApp);
  const [user, setUser] = useState(WebApp.initDataUnsafe.user);

  useEffect(() => {
    // Setup
    initTelegramApp();

    return () => {
      // Cleanup
    };
  }, []);

  return {
    webApp,
    user,
    initData: WebApp.initData,
    platform: WebApp.platform,
    colorScheme: WebApp.colorScheme,
    themeParams: WebApp.themeParams,
    isExpanded: WebApp.isExpanded,
    viewportHeight: WebApp.viewportHeight,
    viewportStableHeight: WebApp.viewportStableHeight
  };
};
```

---

### Стилизация под Telegram

#### Theme Context

```typescript
// src/contexts/ThemeContext.tsx
import { createContext, useContext, useEffect, useState } from 'react';
import { WebApp } from '@twa-dev/sdk';

interface ThemeContextValue {
  isDark: boolean;
  themeParams: Record<string, string>;
}

const ThemeContext = createContext<ThemeContextValue>({
  isDark: true,
  themeParams: {}
});

export const ThemeProvider: FC<PropsWithChildren> = ({ children }) => {
  const [isDark, setIsDark] = useState(
    WebApp.colorScheme === 'dark'
  );

  useEffect(() => {
    // Listen to theme changes
    const handleThemeChange = () => {
      setIsDark(WebApp.colorScheme === 'dark');
    };

    WebApp.onEvent('themeChanged', handleThemeChange);

    return () => {
      WebApp.offEvent('themeChanged', handleThemeChange);
    };
  }, []);

  return (
    <ThemeContext.Provider value={{ isDark, themeParams: WebApp.themeParams }}>
      {children}
    </ThemeContext.Provider>
  );
};
```

#### Using Telegram Colors

```typescript
// src/styles/tokens.ts
import { WebApp } from '@twa-dev/sdk';

export const getTelegramColors = () => ({
  background: WebApp.themeParams.bg_color || '#0A0E27',
  secondary: WebApp.themeParams.secondary_bg_color || '#1A1D35',
  text: WebApp.themeParams.text_color || '#FFFFFF',
  hint: WebApp.themeParams.hint_color || '#B0B3C1',
  link: WebApp.themeParams.link_color || '#FF6B35',
  button: WebApp.themeParams.button_color || '#FF6B35',
  buttonText: WebApp.themeParams.button_text_color || '#FFFFFF'
});
```

**Применение:**
Использовать закатную палитру по умолчанию, но можно добавить опцию "использовать Telegram цвета" в настройках.

---

### BackButton

#### Custom Hook

```typescript
// src/hooks/useBackButton.ts
import { useEffect } from 'react';
import { WebApp } from '@twa-dev/sdk';
import { useNavigate, useLocation } from 'react-router-dom';

export const useBackButton = (callback?: () => void) => {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const isRootRoute = ['/', '/practice', '/groups', '/profile'].includes(
      location.pathname
    );

    if (isRootRoute) {
      WebApp.BackButton.hide();
      return;
    }

    WebApp.BackButton.show();

    const handleBack = () => {
      if (callback) {
        callback();
      } else {
        navigate(-1);
      }
    };

    WebApp.BackButton.onClick(handleBack);

    return () => {
      WebApp.BackButton.offClick(handleBack);
      WebApp.BackButton.hide();
    };
  }, [location, callback, navigate]);
};
```

**Usage:**
```tsx
// В компоненте
useBackButton(() => {
  // Custom back logic
  if (hasUnsavedChanges) {
    showConfirmDialog();
  } else {
    navigate(-1);
  }
});
```

---

### MainButton

#### Custom Hook

```typescript
// src/hooks/useMainButton.ts
import { useEffect } from 'react';
import { WebApp } from '@twa-dev/sdk';

export const useMainButton = (
  text: string,
  onClick: () => void,
  options?: {
    color?: string;
    textColor?: string;
    disabled?: boolean;
    visible?: boolean;
  }
) => {
  useEffect(() => {
    const {
      color = '#FF6B35',
      textColor = '#FFFFFF',
      disabled = false,
      visible = true
    } = options || {};

    if (!visible) {
      WebApp.MainButton.hide();
      return;
    }

    WebApp.MainButton.setText(text);
    WebApp.MainButton.setParams({
      color,
      text_color: textColor,
      is_active: !disabled,
      is_visible: true
    });

    WebApp.MainButton.onClick(onClick);
    WebApp.MainButton.show();

    return () => {
      WebApp.MainButton.offClick(onClick);
      WebApp.MainButton.hide();
    };
  }, [text, onClick, options]);
};
```

**Usage:**
```tsx
// В онбординге
useMainButton('Продолжить', handleNext, {
  disabled: !isValid
});
```

---

### Haptic Feedback

#### Custom Hook

```typescript
// src/hooks/useHaptic.ts
import { useCallback } from 'react';
import { WebApp } from '@twa-dev/sdk';

export const useHaptic = () => {
  const impactOccurred = useCallback(
    (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => {
      if (WebApp.HapticFeedback) {
        WebApp.HapticFeedback.impactOccurred(style);
      }
    },
    []
  );

  const notificationOccurred = useCallback(
    (type: 'error' | 'success' | 'warning') => {
      if (WebApp.HapticFeedback) {
        WebApp.HapticFeedback.notificationOccurred(type);
      }
    },
    []
  );

  const selectionChanged = useCallback(() => {
    if (WebApp.HapticFeedback) {
      WebApp.HapticFeedback.selectionChanged();
    }
  }, []);

  return {
    impactOccurred,
    notificationOccurred,
    selectionChanged
  };
};
```

**Usage:**
```tsx
// В Button компоненте
const { impactOccurred } = useHaptic();

const handleClick = () => {
  impactOccurred('light');
  onClick?.();
};
```

**Стратегия использования:**
- **light** - tap на кнопки, переключение табов
- **medium** - добавление карточки, завершение действия
- **heavy** - завершение сессии, достижение
- **success** - правильный ответ, достижение цели
- **error** - неправильный ответ, ошибка валидации
- **warning** - предупреждения, confirm dialogs
- **selectionChanged** - свайп между карточками, drag

---

### CloudStorage

#### Custom Hook

```typescript
// src/hooks/useCloudStorage.ts
import { useCallback } from 'react';
import { WebApp } from '@twa-dev/sdk';

export const useCloudStorage = () => {
  const setItem = useCallback(async (key: string, value: string) => {
    return new Promise<void>((resolve, reject) => {
      WebApp.CloudStorage.setItem(key, value, (error) => {
        if (error) reject(error);
        else resolve();
      });
    });
  }, []);

  const getItem = useCallback(async (key: string) => {
    return new Promise<string>((resolve, reject) => {
      WebApp.CloudStorage.getItem(key, (error, value) => {
        if (error) reject(error);
        else resolve(value || '');
      });
    });
  }, []);

  const removeItem = useCallback(async (key: string) => {
    return new Promise<void>((resolve, reject) => {
      WebApp.CloudStorage.removeItem(key, (error) => {
        if (error) reject(error);
        else resolve();
      });
    });
  }, []);

  return { setItem, getItem, removeItem };
};
```

**Use cases:**
- Хранить ID активной колоды
- Хранить ID активной темы
- Хранить настройки (card_side, notifications)
- Sync между устройствами

---

### Deep Links

#### Handler

```typescript
// src/utils/deepLinks.ts
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { WebApp } from '@twa-dev/sdk';

export const useDeepLink = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const startParam = WebApp.initDataUnsafe.start_param;

    if (!startParam) return;

    const [action, ...params] = startParam.split('_');

    switch (action) {
      case 'card':
        navigate(`/practice/cards/card/${params[0]}`);
        break;

      case 'deck':
        navigate(`/practice/cards/deck/${params[0]}`);
        break;

      case 'study':
        navigate('/practice/cards/study');
        break;

      case 'exercise':
        navigate('/practice/exercises/session');
        break;

      case 'topic':
        navigate(`/practice/exercises/topic/${params[0]}`);
        break;

      case 'group':
        navigate(`/groups/${params[0]}`);
        break;

      case 'invite':
        const [groupId, token] = params;
        // Show invite modal
        // openInviteModal(groupId, token);
        break;

      case 'premium':
        navigate('/profile/premium');
        break;

      case 'subscription':
        navigate('/profile/subscription');
        break;

      default:
        navigate('/');
    }
  }, [navigate]);
};
```

---

## TypeScript типизация

### API Types

```typescript
// src/types/api.ts

export interface User {
  id: string;
  telegram_id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  is_premium: boolean;
  created_at: string;
}

export interface LanguageProfile {
  id: string;
  user_id: string;
  language: string;
  current_level: CEFRLevel;
  target_level: CEFRLevel;
  goals: string[];
  interface_language: 'ru' | string;
  is_active: boolean;
  created_at: string;
}

export type CEFRLevel = 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2';

export interface Deck {
  id: string;
  profile_id: string;
  name: string;
  is_active: boolean;
  is_group: boolean;
  owner_id?: string;
  owner_name?: string;
  cards_count: number;
  new_cards_count: number;
  created_at: string;
}

export interface Card {
  id: string;
  deck_id: string;
  word: string;
  translation: string;
  example: string;
  example_translation: string;
  lemma: string;
  status: 'new' | 'learning' | 'review';
  next_review: string;
  interval_days: number;
  created_at: string;
}

export interface Topic {
  id: string;
  profile_id: string;
  name: string;
  description: string;
  type: 'grammar' | 'vocabulary' | 'situation';
  is_active: boolean;
  is_group: boolean;
  owner_id?: string;
  owner_name?: string;
  exercises_count: number;
  accuracy: number;
  created_at: string;
}

export interface Exercise {
  id: string;
  topic_id: string;
  question: string;
  prompt: string;
  type: 'free_text' | 'multiple_choice';
  options?: string[];
  correct_answer: string;
  explanation: string;
}

export interface Group {
  id: string;
  owner_id: string;
  name: string;
  description?: string;
  members_count: number;
  max_members: number;
  created_at: string;
}

export interface SessionStats {
  cards_studied: number;
  exercises_completed: number;
  know: number;
  repeat: number;
  dont_know: number;
  correct: number;
  partial: number;
  incorrect: number;
  duration_seconds: number;
}
```

### Component Props Types

```typescript
// src/types/components.ts

export type ButtonVariant = 'primary' | 'secondary' | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';

export type ModalType = 'alert' | 'bottomSheet' | 'fullScreen';
export type ModalSize = 'sm' | 'md' | 'lg' | 'auto';

export type ToastType = 'success' | 'error' | 'info';
export type ToastPosition = 'top' | 'bottom';

export type BadgeVariant = 'default' | 'success' | 'error' | 'warning' | 'info';

export type CardRating = 'know' | 'repeat' | 'dontKnow';
export type ExerciseResult = 'correct' | 'partial' | 'incorrect';
```

### Store Types

```typescript
// src/types/store.ts

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
}

export interface ProfileState {
  profiles: LanguageProfile[];
  activeProfile: LanguageProfile | null;
  loading: boolean;
}

export interface UIState {
  bottomNavVisible: boolean;
  isOnline: boolean;
  notificationCount: number;
}

export interface SettingsState {
  cardSide: 'random' | 'learning' | 'native';
  notificationsEnabled: boolean;
  streakRemindersEnabled: boolean;
  timezone: string;
}
```

---

## Environment Variables

```bash
# .env.example

# API
VITE_API_BASE_URL=https://api.example.com/v1
VITE_API_TIMEOUT=10000

# Telegram
VITE_BOT_USERNAME=YourBot
VITE_BOT_ID=123456789

# Features
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_SENTRY=true

# Development
VITE_MOCK_TELEGRAM=false
VITE_LOG_LEVEL=debug
```

---

## Performance Optimization

### Code Splitting

```typescript
// src/router/routes.tsx
import { lazy } from 'react';

const HomePage = lazy(() => import('@/pages/Home/HomePage'));
const CardsPage = lazy(() => import('@/pages/Practice/Cards/CardsPage'));
const ExercisesPage = lazy(() => import('@/pages/Practice/Exercises/ExercisesPage'));
const GroupsPage = lazy(() => import('@/pages/Groups/GroupsPage'));
const ProfilePage = lazy(() => import('@/pages/Profile/ProfilePage'));
```

### Image Optimization

```typescript
// vite.config.ts
import imagemin from 'vite-plugin-imagemin';

export default defineConfig({
  plugins: [
    imagemin({
      gifsicle: { optimizationLevel: 3 },
      optipng: { optimizationLevel: 7 },
      svgo: { plugins: [{ removeViewBox: false }] }
    })
  ]
});
```

### Bundle Analysis

```bash
npm run build -- --analyze
```

**Target bundle sizes:**
- Initial load: < 200 KB (gzipped)
- Total: < 800 KB (gzipped)
- Time to Interactive: < 3s (3G network)

---

Этот документ описывает полную структуру frontend приложения Telegram Mini App для изучения языков с ИИ, включая технологический стек, компоненты, интеграцию с Telegram и TypeScript типизацию.
