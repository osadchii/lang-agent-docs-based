# Lang Agent Mini App - Frontend

Telegram Mini App для изучения языков с ИИ-преподавателем.

## Технологии

- **React 18.2+** - UI библиотека
- **TypeScript 5.0+** - строгая типизация
- **Vite 7+** - быстрая сборка
- **React Router 6+** - роутинг
- **@twa-dev/sdk** - Telegram WebApp API
- **Axios** - HTTP клиент

## Установка

```bash
# Установить зависимости
npm install

# Создать .env файл (скопируйте из .env.example)
cp .env.example .env
```

## Разработка

```bash
# Запустить dev-сервер
npm run dev

# Открыть в браузере
# http://localhost:5173
```

## Сборка

```bash
# Production сборка
npm run build

# Preview production build
npm run preview
```

## Структура проекта

```
frontend/
  src/
    api/
    components/
      ui/                # Button, Card, Input/Textarea, Modal/BottomSheet, Badge, Progress, Tabs, Toast, Skeleton, EmptyState
    hooks/
      useTelegram.ts
    pages/
      Home/
      Error/
      UiKit/             # Экран-превью UI-kit (/ui-kit)
    router/
      index.tsx
    styles/
      globals.css
      tokens.ts          # Design tokens (цвета/радиусы/шрифты)
      theme.tsx          # ThemeProvider с Telegram-theme params
    utils/
      classNames.ts
    types/
      telegram.ts
    App.tsx
    main.tsx
  index.html
  package.json
  vite.config.ts
```

## UI-kit и темы

- ???????? `src/components/ui`: Button, Card, Input/Textarea, Modal/BottomSheet, Badge, Progress, Tabs, Toast, Skeleton, EmptyState
- `ThemeProvider` (`src/styles/theme.tsx`) ???????? tokens (`src/styles/tokens.ts`), ???????? Telegram `themeParams` ? ????????? ??????? ??????? ??????????
- ????? ????????: ??????? `/ui-kit` ?? dev-??????? (Vite)

## Интеграция с Telegram

Приложение использует Telegram WebApp API для:

- Получения данных пользователя
- Интеграции с темой Telegram
- BackButton и MainButton
- Haptic Feedback
- Cloud Storage

## Особенности

### Закатная палитра

Приложение использует закатную цветовую палитру:

- Background: `#0A0E27`
- Secondary: `#1A1D35`
- Accent: `#FF6B35`, `#FF8C5A`, `#FF5E78`

### Mock режим для разработки

В dev-режиме используется mock Telegram WebApp API для тестирования без реального Telegram окружения.

## Переменные окружения

См. `.env.example` для списка всех доступных переменных.

## Следующие шаги

После базового бутстрапа будут добавлены:

- API клиент и интеграция с backend
- Аутентификация через Telegram initData
- Компоненты UI (Button, Card, Modal и т.д.)
- Страницы для карточек, упражнений, групп
- State management (React Query + Zustand)

## Документация

Полная документация по frontend находится в `../docs/`:

- `frontend-structure.md` - структура и технологии
- `frontend-screens.md` - дизайн экранов
- `frontend-navigation.md` - навигация и роутинг
- `backend-telegram.md` - интеграция с Telegram

## Задачи из to-do.md

**Задача 22: ✅ Бутстрап фронтенда**

- ✅ Vite + React + TS
- ✅ SDK @twa-dev/sdk
- ✅ Страницы: Home (плейсхолдер), Error
- ✅ Интеграция Telegram WebApp initData
- ✅ Acceptance: билд/дев-сервер работает, отрисовывается стартовый экран
