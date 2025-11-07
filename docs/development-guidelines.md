# Принципы разработки

## Code Style

### Python (Backend)
- PEP 8
- Black для форматирования
- Flake8 для линтинга
- Type hints обязательны
- Docstrings для публичных функций и классов

### TypeScript/React (Frontend)
- ESLint + Prettier
- Функциональные компоненты и hooks
- Типизация обязательна (no any)
- Props интерфейсы для всех компонентов

## Git Workflow

### Branches
- `main` - продакшн
- `develop` - разработка (опционально)
- `feature/название` - фичи
- `bugfix/название` - баг-фиксы
- `hotfix/название` - срочные фиксы для прода

### Commits
TODO: соглашения о commit messages (Conventional Commits)

### Pull Requests
TODO: требования к PR (тесты, ревью, и т.д.)

## Архитектурные принципы

### Backend
- Слоистая архитектура (handlers → services → repositories)
- Dependency Injection
- Разделение бизнес-логики и инфраструктуры

### Frontend
- Компонентный подход
- Разделение логики и представления
- Reusable компоненты

## Тестирование

### Backend
- Pytest
- Покрытие: стремиться к >80%
- Unit tests для бизнес-логики
- Integration tests для API

### Frontend
- Jest + React Testing Library
- Unit tests для утилит и hooks
- Component tests для UI

## Code Review

### Что проверяем
- Соответствие требованиям
- Читаемость кода
- Покрытие тестами
- Безопасность
- Производительность

### Процесс
TODO: описать процесс ревью

## Documentation

### Код
- Комментарии для сложной логики
- Docstrings/JSDoc для публичных API

### Проект
- Обновление docs/ при изменениях
- README для каждого модуля при необходимости

## Performance

### Backend
- Оптимизация SQL запросов
- Кэширование частых запросов
- Async где возможно

### Frontend
- Code splitting
- Lazy loading компонентов
- Оптимизация re-renders

## Security Best Practices
TODO: список правил безопасности
