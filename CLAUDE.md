# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Language Learning AI Assistant** - A Telegram bot for language learning with an AI teacher. The project includes spaced repetition (SRS), LLM-powered exercise generation, group learning, and Telegram Mini App integration.

This is a **documentation-driven project**: all development follows specifications in `docs/`. The documentation is the source of truth, not the code.

## Critical Principles

### Documentation is Law
**CRITICALLY IMPORTANT:** Before starting ANY task:
1. Read the relevant documentation in `docs/` first
2. All architectural decisions must follow `docs/architecture.md`
3. All API endpoints must match `docs/backend-api.md` exactly
4. All business logic must implement use cases from `docs/use-cases.md`
5. **If code doesn't match documentation, the documentation is correct** - update the code

### Small Files, Single Responsibility
- **Backend (Python):** Max 300 lines per file, one class per file
- **Frontend (TypeScript):** Max 250 lines per component
- **One responsibility per file/class/component**
- If a file exceeds these limits, it must be split into smaller modules

### Testing is Mandatory
- **Backend:** Minimum 85% coverage (100% for critical modules: auth, payments, repositories)
- **Frontend:** Minimum 75% coverage (100% for critical components: auth flow, payment flow, card/exercise sessions)
- Tests must cover all edge cases
- CI must pass before any merge

## Technology Stack

### Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI (async)
- **ORM:** SQLAlchemy 2.0+ (async)
- **Database:** PostgreSQL 15+
- **Cache:** Redis 7+
- **Telegram Bot:** python-telegram-bot 20+
- **LLM:** OpenAI Python SDK (GPT-4.1-mini)
- **Auth:** JWT (python-jose)
- **Payments:** Stripe
- **Testing:** pytest, pytest-asyncio, pytest-cov

### Frontend
- **Language:** TypeScript 5.0+ (strict mode)
- **Framework:** React 18.2+
- **Build Tool:** Vite 4+
- **State Management:** React Query + Zustand
- **Telegram:** @twa-dev/sdk
- **HTTP Client:** Axios
- **Testing:** Vitest + React Testing Library

## Common Commands

### Backend Development

```bash
cd backend

# Install dependencies
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload

# Run tests
pytest                                    # All tests
pytest tests/unit/                        # Unit tests only
pytest --cov=app --cov-report=html        # With coverage report
pytest tests/unit/services/test_flashcards_service.py  # Single test file

# Code quality
black app/                                # Format code
isort app/                                # Sort imports
ruff check app/                           # Lint
mypy app/                                 # Type checking

# Database migrations (after Alembic is set up)
alembic revision --autogenerate -m "Description"  # Create migration
alembic upgrade head                              # Apply migrations
alembic downgrade -1                              # Rollback last migration
```

### Frontend Development (when implemented)

```bash
cd frontend

# Install dependencies
npm install

# Development server
npm run dev

# Tests
npm test                  # Run tests
npm test -- --coverage    # With coverage
npm test -- --watch       # Watch mode

# Code quality
npm run lint              # ESLint
npm run typecheck         # TypeScript check
npm run format            # Prettier

# Build
npm run build
```

### Docker Development Environment

```bash
# Start PostgreSQL + Redis
docker-compose -f docker-compose.dev.yml up -d

# Stop services
docker-compose -f docker-compose.dev.yml down

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Restart services
docker-compose -f docker-compose.dev.yml restart
```

## Architecture Overview

### Backend: Layered Architecture

```
API Layer (FastAPI)
├── Bot Handler (POST /telegram-webhook/{bot_token})
└── REST API (GET/POST/PATCH/DELETE /api/*)
    │
    ▼
Business Logic Layer (Services)
├── FlashcardsService - Card creation, SRS algorithm (SM-2)
├── ExercisesService - Exercise generation/checking
├── LLMService - OpenAI API wrapper, prompt management
├── AuthService - Telegram initData validation (HMAC-SHA256)
├── SubscriptionService - Stripe integration
└── UserService, GroupsService, StatsService, MediaService
    │
    ▼
Data Access Layer (Repositories)
├── BaseRepository - Common CRUD operations
└── CardRepository, UserRepository, ProfileRepository, etc.
    │
    ▼
Models (SQLAlchemy ORM)
└── User, LanguageProfile, Deck, Card, Topic, etc.
```

**Key Rule:** Handlers only validate input and call services. Business logic lives in services, not handlers.

### Critical Security: Telegram Authentication

**NEVER trust user_id from client directly!**

The only secure way to get user_id:
1. Frontend gets `initData` from `window.Telegram.WebApp.initData`
2. Frontend sends to `POST /api/auth/validate`
3. Backend validates HMAC-SHA256 signature (see `docs/backend-auth.md`)
4. Backend extracts user_id from validated initData
5. Backend returns JWT token
6. All subsequent requests use JWT in Authorization header

**Implementation:** See `docs/backend-auth.md` for complete HMAC validation algorithm.

## Database Schema

Key tables (see `docs/backend-database.md` for full schema):
- `users` - Telegram users with subscription status
- `language_profiles` - Multiple language learning profiles per user
- `decks` - Card collections (one active per profile)
- `cards` - Flashcards with SRS intervals (SM-2 algorithm)
- `topics` - Exercise topics
- `exercise_history` - Exercise results with timestamps
- `conversation_history` - LLM dialog history (last 20 msgs or 24h)
- `groups`, `group_members`, `group_materials` - Group learning
- `subscriptions` - Stripe subscription data

**Important constraints:**
- Only ONE active profile per user
- Only ONE active deck per profile
- Only ONE active topic per profile
- Unique lemma per profile (prevents duplicate cards)

## Key Algorithms

### SM-2 Spaced Repetition (Simplified)

Used for flashcard intervals:
```python
def calculate_next_interval(current_interval: int, rating: str) -> int:
    if rating == 'dont_know':
        return 1  # Reset to 1 day
    elif rating == 'repeat':
        return current_interval  # No change
    else:  # 'know'
        return round(current_interval * 2.5)  # Increase by 2.5x
```

### Card Selection Priority

1. Overdue cards (next_review <= today) - sorted by most overdue
2. New cards (never studied)
3. Future cards are not shown

Implementation: `GET /api/cards/next` (see `docs/backend-flashcards.md`)

### LLM Token Management

- Conversation history: max 20 messages OR 24 hours
- Max 8000 tokens per history (trim oldest if exceeded)
- Count tokens before sending to OpenAI
- Track costs: free (50 msgs/day), premium (500 msgs/day)

## Rate Limits & Tiers

### Free Tier
- 50 LLM messages/day
- 10 exercises/day
- 200 cards max
- 1 language profile
- 1 group

### Premium Tier ($5/month or $50/year)
- 500 LLM messages/day
- Unlimited exercises
- Unlimited cards
- Unlimited profiles
- Unlimited groups
- No ads (future feature)

Check limits: `docs/backend-subscriptions.md`

## Essential Documentation Files

Before working on features, **MUST READ** these docs:

### Core Architecture
- `docs/architecture.md` - System architecture, component interaction, data flow
- `docs/development-guidelines.md` - Code style, testing, Git workflow, file size limits

### Backend Implementation
- `docs/backend-api.md` - Complete API specification with examples
- `docs/backend-database.md` - Database schema, indices, constraints
- `docs/backend-auth.md` - Telegram initData validation (CRITICAL for security)
- `docs/backend-flashcards.md` - SRS algorithm, card lifecycle
- `docs/backend-exercises.md` - Exercise generation/checking
- `docs/backend-llm.md` - LLM client, prompt structure, token management
- `docs/backend-telegram.md` - Bot commands, callbacks, message formatting
- `docs/backend-subscriptions.md` - Stripe integration, webhooks
- `docs/backend-bot-responses.md` - Bot message templates and flows

### Frontend (when implemented)
- `docs/frontend-structure.md` - Component architecture, state management
- `docs/frontend-screens.md` - All screens with wireframes
- `docs/frontend-navigation.md` - Routing structure

### Business Logic
- `docs/use-cases.md` - User scenarios (UC-0 through UC-4)
- `docs/use-cases-questions.md` - Use case clarifications

### DevOps
- `docs/deployment.md` - Docker, environment variables, deployment process
- `docs/ci-cd.md` - GitHub Actions workflows

## Development Workflow

### Starting a New Task

1. **Read documentation first:**
   ```bash
   # Example: Working on flashcards feature
   cat docs/backend-flashcards.md
   cat docs/backend-api.md  # Find relevant endpoints
   cat docs/use-cases.md    # Find UC-2, UC-3
   ```

2. **Check roadmap:**
   ```bash
   cat to-do.md  # Find task details and dependencies
   ```

3. **Create feature branch:**
   ```bash
   git checkout -b feature/LANG-123-flashcard-service
   ```

4. **Write tests first** (TDD):
   ```bash
   # Create test file
   touch backend/tests/unit/services/test_flashcards_service.py
   # Write tests based on documentation
   ```

5. **Implement feature** following docs exactly

6. **Verify quality:**
   ```bash
   # Backend
   pytest --cov=app --cov-fail-under=85
   black app/
   ruff check app/
   mypy app/

   # Frontend
   npm test -- --coverage --run
   npm run lint
   npm run typecheck
   ```

7. **Create PR** with description from template in `docs/development-guidelines.md`

### Git Commit Messages

Use Conventional Commits format:
```bash
# Feature
git commit -m "feat(cards): add SM-2 spaced repetition algorithm"

# Fix
git commit -m "fix(auth): validate Telegram initData timestamp correctly"

# Docs
git commit -m "docs(api): update cards endpoint examples"

# Refactor
git commit -m "refactor(services): extract SM-2 algorithm to separate class"
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`

### Code Review Requirements

Before merge, ensure:
- [ ] Minimum 2 approvals
- [ ] All CI checks pass
- [ ] Test coverage ≥ 85% (backend) / 75% (frontend)
- [ ] Documentation updated if needed
- [ ] No hardcoded secrets
- [ ] Files < 300 lines (backend) / 250 lines (frontend)
- [ ] All comments resolved

## Common Patterns

### Backend: Service with Repository

```python
# services/flashcards_service.py
from app.repositories.card_repository import CardRepository
from app.services.llm_service import LLMService

class FlashcardsService:
    """Flashcard business logic.

    See docs/backend-flashcards.md for complete specification.
    """

    def __init__(self, card_repo: CardRepository, llm_service: LLMService):
        self.card_repo = card_repo
        self.llm_service = llm_service

    async def create_card(self, word: str, deck_id: UUID, profile_id: UUID) -> Card:
        """Create flashcard with LLM-generated content.

        Algorithm:
        1. Get lemma (base form) of word
        2. Check for duplicates by lemma + profile_id
        3. Generate translation + example via LLM
        4. Save to database

        Raises:
            DuplicateCardError: Card with this lemma already exists
            LimitReachedError: User reached card limit (free tier)
        """
        # Implementation follows docs/backend-flashcards.md
        pass
```

### Backend: API Endpoint with Dependencies

```python
# api/endpoints/cards.py
from fastapi import APIRouter, Depends, HTTPException
from app.services.flashcards_service import FlashcardsService
from app.core.auth import get_current_user

router = APIRouter()

@router.post("/cards", status_code=201)
async def create_card(
    data: CreateCardRequest,
    current_user: User = Depends(get_current_user),
    service: FlashcardsService = Depends(get_flashcards_service)
):
    """Create flashcard. See docs/backend-api.md#create-cards"""
    try:
        card = await service.create_card(
            word=data.word,
            deck_id=data.deck_id,
            profile_id=current_user.active_profile_id
        )
        return CardResponse.from_orm(card)
    except DuplicateCardError as e:
        raise HTTPException(status_code=409, detail=str(e))
```

### Frontend: Custom Hook with React Query

```typescript
// hooks/useCards.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cardsApi } from '@/api/endpoints/cards';

/**
 * Hook for managing flashcards.
 *
 * See docs/frontend-structure.md for state management patterns.
 */
export const useCards = (deckId: string) => {
  const queryClient = useQueryClient();

  const { data: cards, isLoading } = useQuery({
    queryKey: ['cards', deckId],
    queryFn: () => cardsApi.getCards(deckId),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  const rateCardMutation = useMutation({
    mutationFn: ({ cardId, rating }: { cardId: string; rating: CardRating }) =>
      cardsApi.rateCard(cardId, rating),
    onSuccess: () => {
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

## Troubleshooting

### Backend Issues

**Problem:** Alembic migration fails
```bash
# Check database connection
docker-compose -f docker-compose.dev.yml ps
# View PostgreSQL logs
docker-compose -f docker-compose.dev.yml logs postgres
# Reset database (DEVELOPMENT ONLY!)
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
alembic upgrade head
```

**Problem:** Tests failing with database errors
```bash
# Ensure test database is isolated
# Check tests/conftest.py uses in-memory SQLite or separate test DB
pytest tests/unit/ -v  # Should not touch real database
```

**Problem:** Import errors
```bash
# Ensure you're in venv and installed requirements
source venv/bin/activate
pip install -r requirements.txt
# Check PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Common Mistakes to Avoid

1. **❌ Trusting user_id from client:** Always validate Telegram initData
2. **❌ Business logic in handlers:** Move to services
3. **❌ Ignoring rate limits:** Check both free/premium tiers
4. **❌ Files > 300 lines:** Split into smaller modules
5. **❌ Missing tests:** Aim for 85%+ coverage
6. **❌ Hardcoded secrets:** Use environment variables
7. **❌ Not reading docs first:** Documentation is the source of truth
8. **❌ N+1 queries:** Use eager loading (selectinload)

## Project Status

Current status: **Foundation Complete** (Task 0 from `to-do.md`)

Next tasks (see `to-do.md` for details):
1. Database migrations (Alembic + all tables)
2. Authentication (JWT + Telegram initData validation)
3. Users & Profiles CRUD
4. Flashcards (Decks/Cards + SRS)
5. LLM service & prompts
6. Exercises/Topics
7. Telegram Bot
8. Subscriptions (Stripe)
9. Frontend (React Mini App)
10. CI/CD & Deployment

## Important Links

- API Docs (dev): http://localhost:8000/api/docs
- Health Check: http://localhost:8000/api/health
- Repository: See `.git/config` for remote URL
- Roadmap: `to-do.md`
- Architecture Diagrams: See `docs/architecture.md`

## Quick Reference

### Environment Variables

See `.env.example` for full list. Critical variables:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/lang_agent

# Redis
REDIS_URL=redis://localhost:6379/0

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_WEBHOOK_URL=https://api.example.com/telegram-webhook

# OpenAI
OPENAI_API_KEY=sk-...

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# JWT
JWT_SECRET_KEY=<generate-random-256-bit-key>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30

# Environment
ENVIRONMENT=development  # or production
APP_VERSION=0.1.0
```

### File Structure

```
backend/
├── app/
│   ├── api/           # FastAPI routers and endpoints
│   ├── core/          # Configuration, logging, auth
│   ├── models/        # SQLAlchemy ORM models (to be added)
│   ├── repositories/  # Data access layer (to be added)
│   ├── services/      # Business logic (to be added)
│   └── main.py        # Application entry point
├── tests/
│   ├── unit/          # Unit tests
│   ├── integration/   # Integration tests
│   └── conftest.py    # Test fixtures
├── prompts/           # LLM prompt templates (to be added)
├── Dockerfile
└── requirements.txt

frontend/              # React Mini App (to be added)
docs/                  # Complete project documentation
.github/workflows/     # CI/CD pipelines (to be added)
```

## Need Help?

1. **Check documentation first:** `docs/` has detailed specs
2. **Review roadmap:** `to-do.md` shows implementation order
3. **Check examples:** Look at existing code in `backend/app/`
4. **Run tests:** `pytest -v` to see what's expected
5. **Check architecture:** `docs/architecture.md` shows how components interact

Remember: **Documentation is the source of truth.** When in doubt, follow the specs in `docs/`.
