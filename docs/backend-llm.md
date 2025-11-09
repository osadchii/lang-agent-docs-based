# Работа с LLM

## Обзор

LLM является центральным компонентом системы, обеспечивающим:
- Диалоговый интерфейс (ИИ-преподаватель)
- Генерацию учебных материалов (карточки, упражнения)
- Анализ и проверку ответов пользователей
- Адаптацию под уровень и цели обучения
- Обработку мультимодального контента (текст, изображения, голос)

---

## Выбор провайдера

### Основной провайдер: OpenAI

**Модели:**

1. **GPT-4.1-mini** (или gpt-4o-mini) - основная модель для всех текстовых задач
   - **Использование:** диалог, генерация контента, проверка ответов
   - **Причины выбора:**
     - Отличное качество при доступной цене
     - Поддержка русского и множества языков
     - Быстрая работа (latency < 2s)
     - Большой контекст (128K токенов)
     - Structured outputs (JSON mode)
   - **Цена:** ~$0.15/1M input tokens, ~$0.60/1M output tokens

2. **Whisper** - Speech-to-Text
   - **Использование:** транскрипция голосовых сообщений
   - **Поддержка:** 50+ языков, автоопределение языка
   - **Цена:** $0.006/минута

3. **GPT-4 Vision** (опционально) - для улучшения OCR
   - **Использование:** анализ изображений с текстом
   - **Цена:** ~$5/1M input tokens

**SDK:**
```bash
pip install openai==1.6.1
```

### Альтернативные провайдеры (для будущих версий)

**Anthropic Claude:**
- Преимущества: более длинный контекст (200K), лучше в рассуждениях
- Недостатки: дороже, меньше поддержка языков
- Может быть использован для премиум пользователей

**Open-source модели (Llama, Mistral):**
- Для self-hosting, если нужна полная конфиденциальность
- Требуют значительных вычислительных ресурсов

---

## Промпт-инжиниринг

### Архитектура промптов

**Структура директории:**
```
backend/
├── prompts/
│   ├── system/
│   │   ├── teacher.txt              # Базовый system prompt
│   │   └── teacher_profiles.txt     # Дополнение под профили
│   ├── cards/
│   │   ├── generate_card.txt        # Генерация карточки
│   │   ├── check_duplicate.txt      # Проверка дубликатов
│   │   └── suggest_words.txt        # Предложение слов из текста
│   ├── exercises/
│   │   ├── generate_free_text.txt   # Генерация free-text упражнения
│   │   ├── generate_multiple_choice.txt  # Multiple choice
│   │   ├── check_answer.txt         # Проверка ответа
│   │   └── suggest_topics.txt       # Рекомендации тем
│   ├── dialog/
│   │   ├── detect_intent.txt        # Определение намерения
│   │   ├── generate_response.txt    # Генерация ответа
│   │   └── off_topic.txt            # Ответ на нерелевантные вопросы
│   └── utils/
│       ├── translate.txt            # Перевод
│       ├── explain_grammar.txt      # Объяснение грамматики
│       └── get_lemma.txt            # Определение леммы
```

**Формат промптов (Jinja2):**
```python
# prompts/system/teacher.txt
You are a professional language teacher specializing in {{ language }}.

Your student is learning {{ language }} and has the following profile:
- Current level: {{ current_level }} (CEFR scale)
- Target level: {{ target_level }}
- Learning goals: {{ goals | join(', ') }}
- Interface language: {{ interface_language }}

Your teaching style:
- Clear, confident, and comprehensive
- Adapt explanations to the student's level
- Use examples appropriate for their level
- Be encouraging but honest about mistakes
- Focus on practical language use

When responding:
- Answer in {{ interface_language }} (unless asked otherwise)
- Keep responses concise but complete
- Use formatting (bold, italics) for emphasis
- Provide examples in {{ language }} with translations
```

---

### Системные промпты

#### 1. Базовый system prompt (teacher.txt)

**Назначение:** Определяет роль и стиль ИИ-преподавателя

**Параметры:**
- `language` - изучаемый язык (Spanish, German, etc.)
- `language_name` - название на русском (испанский, немецкий)
- `current_level` - текущий уровень (A1-C2)
- `target_level` - целевой уровень
- `goals` - цели обучения (work, travel, study, etc.)
- `interface_language` - язык интерфейса (ru или изучаемый)

**Пример промпта:**
```jinja2
You are a professional {{ language }} teacher helping Russian-speaking students.

Student Profile:
- Learning: {{ language_name }} ({{ language }})
- Current level: {{ current_level }} (CEFR)
- Target level: {{ target_level }}
- Goals: {{ goals | join(', ') }}
- Interface language: {{ interface_language }}

Teaching Principles:
1. Adapt complexity to {{ current_level }} level
2. Provide clear, actionable explanations
3. Use real-world examples
4. Be encouraging but honest
5. Focus on practical communication

Response Format:
- Answer in {{ interface_language }}
- Use simple language for explanations
- Provide examples with translations
- Highlight key points with **bold**
- Keep responses under 500 words unless asked for more

Special Instructions:
- If asked off-topic questions, politely redirect to language learning
- If unsure, admit it and provide best guidance
- Always validate grammar and vocabulary usage
- Encourage active practice
```

**Генерация:**
```python
from jinja2 import Template

def get_system_prompt(profile: LanguageProfile) -> str:
    template = Template(load_prompt('system/teacher.txt'))
    return template.render(
        language=profile.language,
        language_name=profile.language_name,
        current_level=profile.current_level,
        target_level=profile.target_level,
        goals=profile.goals,
        interface_language=profile.interface_language
    )
```

---

#### 2. Определение намерения (detect_intent.txt)

**Назначение:** Определить тип запроса пользователя

**Возможные намерения:**
- `translate` - перевод слова/фразы
- `explain_grammar` - объяснение грамматики
- `check_text` - проверка текста на ошибки
- `add_card` - просьба добавить слово в карточки
- `practice` - запрос на упражнение
- `general` - общий вопрос о языке
- `off_topic` - вопрос не по теме

**Промпт:**
```jinja2
Analyze the user's message and determine their intent.

Message: "{{ user_message }}"

Possible intents:
- translate: asking for translation
- explain_grammar: asking about grammar rules
- check_text: asking to check their text
- add_card: explicitly asking to add words to flashcards
- practice: asking for exercises or practice
- general: general question about the language
- off_topic: unrelated to language learning

Respond in JSON format:
{
  "intent": "translate",
  "confidence": 0.95,
  "entities": {
    "word": "casa",
    "context": "..."
  }
}
```

**Обработка:**
```python
async def detect_intent(user_message: str, profile: LanguageProfile) -> Intent:
    prompt = render_prompt('dialog/detect_intent.txt', {
        'user_message': user_message
    })

    response = await llm_client.chat(
        messages=[
            {'role': 'system', 'content': get_system_prompt(profile)},
            {'role': 'user', 'content': prompt}
        ],
        response_format={'type': 'json_object'}
    )

    return Intent.parse_obj(json.loads(response.content))
```

---

### Контекст диалога

#### Управление историей

**Лимиты (из use-cases.md):**
- Последние **20 сообщений** (10 пар вопрос-ответ)
- ИЛИ сообщения за последние **24 часа** (что меньше)
- Максимум **8000 токенов** на контекст истории

**Хранение:**
- Полная история хранится в БД (таблица `conversation_history`)
- В LLM передается только релевантная часть

**Структура:**
```python
from dataclasses import dataclass

@dataclass
class ConversationMessage:
    role: Literal['user', 'assistant']
    content: str
    timestamp: datetime
    tokens: int  # Предвычисленное количество токенов

async def get_conversation_history(
    user_id: str,
    profile_id: str,
    max_messages: int = 20,
    max_hours: int = 24,
    max_tokens: int = 8000
) -> list[ConversationMessage]:
    """
    Получает историю диалога с учетом лимитов.
    """
    # 1. Получаем последние N сообщений из БД
    messages = await db.query(ConversationHistory).filter(
        ConversationHistory.user_id == user_id,
        ConversationHistory.profile_id == profile_id,
        ConversationHistory.timestamp >= datetime.utcnow() - timedelta(hours=max_hours)
    ).order_by(
        ConversationHistory.timestamp.desc()
    ).limit(max_messages).all()

    # 2. Обратный порядок (от старых к новым)
    messages = list(reversed(messages))

    # 3. Обрезаем по токенам
    total_tokens = 0
    result = []

    for msg in reversed(messages):  # От новых к старым для обрезки
        if total_tokens + msg.tokens > max_tokens:
            break
        result.insert(0, msg)  # Добавляем в начало
        total_tokens += msg.tokens

    return result

async def format_messages_for_llm(
    system_prompt: str,
    conversation_history: list[ConversationMessage],
    current_message: str
) -> list[dict]:
    """
    Форматирует сообщения для OpenAI API.
    """
    messages = [{'role': 'system', 'content': system_prompt}]

    # Добавляем историю
    for msg in conversation_history:
        messages.append({
            'role': msg.role,
            'content': msg.content
        })

    # Добавляем текущее сообщение
    messages.append({'role': 'user', 'content': current_message})

    return messages
```

**Подсчет токенов:**
```python
import tiktoken

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Подсчитывает количество токенов в тексте.
    """
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

async def save_message_with_tokens(
    user_id: str,
    profile_id: str,
    role: str,
    content: str
):
    """
    Сохраняет сообщение с предвычисленными токенами.
    """
    tokens = count_tokens(content)

    message = ConversationHistory(
        user_id=user_id,
        profile_id=profile_id,
        role=role,
        content=content,
        tokens=tokens,
        timestamp=datetime.utcnow()
    )

    db.add(message)
    await db.commit()
```

---

### Промпты для специфических задач

#### 1. Генерация карточки (generate_card.txt)

**Назначение:** Создать карточку со словом, переводом и примерами

**Промпт:**
```jinja2
Generate a flashcard for the word: "{{ word }}"

Requirements:
1. Provide the word in its base form (lemma)
2. Translate to Russian
3. Create an example sentence in {{ language }} (appropriate for {{ level }} level)
4. Translate the example to Russian

Consider:
- User's level: {{ level }}
- User's goals: {{ goals | join(', ') }}
- The example should be practical and memorable

Respond in JSON format:
{
  "word": "casa",
  "lemma": "casa",
  "translation": "дом",
  "example": "Mi casa es tu casa",
  "example_translation": "Мой дом - твой дом",
  "notes": "common expression meaning 'make yourself at home'"
}
```

**Обработка:**
```python
async def generate_card_content(
    word: str,
    profile: LanguageProfile
) -> CardContent:
    prompt = render_prompt('cards/generate_card.txt', {
        'word': word,
        'language': profile.language,
        'level': profile.current_level,
        'goals': profile.goals
    })

    response = await llm_client.chat(
        messages=[
            {'role': 'system', 'content': get_system_prompt(profile)},
            {'role': 'user', 'content': prompt}
        ],
        response_format={'type': 'json_object'},
        temperature=0.7
    )

    return CardContent.parse_obj(json.loads(response.content))
```

---

#### 2. Проверка дубликатов (check_duplicate.txt)

**Назначение:** Определить лемму (начальную форму) для проверки дубликатов

**Промпт:**
```jinja2
Determine the lemma (base form) of the word: "{{ word }}" in {{ language }}.

The lemma is:
- For nouns: singular form (with article if needed)
- For verbs: infinitive
- For adjectives: masculine singular (if applicable)

Examples:
- Spanish: "casas" → "casa", "comí" → "comer"
- German: "Häuser" → "das Haus", "gehst" → "gehen"
- English: "houses" → "house", "went" → "go"

Respond with only the lemma, no explanation.
```

**Обработка:**
```python
async def get_lemma(word: str, language: str) -> str:
    prompt = render_prompt('utils/get_lemma.txt', {
        'word': word,
        'language': language
    })

    response = await llm_client.chat(
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.0,  # Deterministic
        max_tokens=20
    )

    return response.content.strip()

async def check_duplicate(
    word: str,
    profile_id: str,
    language: str
) -> bool:
    """
    Проверяет, существует ли карточка с такой леммой.
    """
    lemma = await get_lemma(word, language)

    existing_card = await db.query(Card).filter(
        Card.profile_id == profile_id,
        Card.lemma == lemma.lower(),
        Card.deleted == False
    ).first()

    return existing_card is not None
```

---

#### 3. Генерация упражнения (generate_free_text.txt)

**Назначение:** Сгенерировать упражнение со свободным вводом

**Промпт:**
```jinja2
Generate a {{ type }} exercise for the topic: "{{ topic_name }}"

Topic description: {{ topic_description }}
Student level: {{ level }}
Exercise type: {{ type }}

Requirements:
1. Create a clear question/instruction
2. Provide a prompt (sentence to translate or complete)
3. The difficulty should match {{ level }} level
4. Focus on {{ topic_type }} (grammar/vocabulary/situation)

{% if type == 'free_text' %}
The student will write their answer freely.
{% elif type == 'multiple_choice' %}
Provide 4 options:
- 1 correct answer
- 3 plausible but incorrect options (common mistakes)
{% endif %}

Respond in JSON format:
{
  "question": "Переведите на {{ language }}:",
  "prompt": "Я работал в этой компании два года",
  "correct_answer": "He trabajado en esta empresa dos años",
  "hint": "Think about whether the action is connected to the present",
  "explanation": "Use Pretérito Perfecto because the action is connected to the present (still relevant)",
  "alternatives": ["Trabajé en esta empresa dos años"],
  {% if type == 'multiple_choice' %}
  "options": [
    "Trabajo en esta empresa dos años",
    "Trabajé en esta empresa dos años",
    "He trabajado en esta empresa dos años",
    "Trabajaba en esta empresa dos años"
  ],
  "correct_index": 2
  {% endif %}
}
```

**Обработка:**
```python
async def generate_exercise(
    topic: Topic,
    profile: LanguageProfile,
    exercise_type: Literal['free_text', 'multiple_choice']
) -> Exercise:
    prompt = render_prompt('exercises/generate_free_text.txt', {
        'topic_name': topic.name,
        'topic_description': topic.description,
        'topic_type': topic.type,
        'level': profile.current_level,
        'language': profile.language,
        'type': exercise_type
    })

    response = await llm_client.chat(
        messages=[
            {'role': 'system', 'content': get_system_prompt(profile)},
            {'role': 'user', 'content': prompt}
        ],
        response_format={'type': 'json_object'},
        temperature=0.8  # Вариативность для разных упражнений
    )

    return Exercise.parse_obj(json.loads(response.content))
```

---

#### 4. Проверка ответа (check_answer.txt)

**Назначение:** Проверить ответ пользователя на упражнение

**Промпт:**
```jinja2
Check the student's answer to the exercise.

Exercise:
Question: {{ question }}
Prompt: {{ prompt }}
Correct answer: {{ correct_answer }}

Student's answer: {{ user_answer }}

Evaluation criteria:
1. Grade as "correct", "partial", or "incorrect"
2. Accept synonyms and alternative correct forms
3. Ignore minor typos (1-2 characters)
4. Consider grammatically correct alternatives
5. Be strict with grammar if it's a grammar exercise
6. Student level: {{ level }} - be encouraging but honest

Provide:
- Result (correct/partial/incorrect)
- Explanation of mistakes (if any)
- Correct answer
- Alternative correct answers (if applicable)
- Encouragement and guidance for improvement

Respond in JSON format:
{
  "result": "correct|partial|incorrect",
  "explanation": "Правильно! Вы использовали Pretérito Perfecto, потому что...",
  "correct_answer": "He trabajado en esta empresa dos años",
  "alternatives": ["Trabajé en esta empresa dos años (also correct but different tense)"],
  "feedback": "Отлично! Продолжайте практиковаться.",
  "mistakes": [
    {
      "type": "grammar",
      "description": "Wrong tense used",
      "suggestion": "Use Pretérito Perfecto instead of Presente"
    }
  ]
}
```

**Обработка:**
```python
async def check_exercise_answer(
    exercise: Exercise,
    user_answer: str,
    profile: LanguageProfile
) -> ExerciseResult:
    prompt = render_prompt('exercises/check_answer.txt', {
        'question': exercise.question,
        'prompt': exercise.prompt,
        'correct_answer': exercise.correct_answer,
        'user_answer': user_answer,
        'level': profile.current_level
    })

    response = await llm_client.chat(
        messages=[
            {'role': 'system', 'content': get_system_prompt(profile)},
            {'role': 'user', 'content': prompt}
        ],
        response_format={'type': 'json_object'},
        temperature=0.3  # Более детерминированная оценка
    )

    return ExerciseResult.parse_obj(json.loads(response.content))
```

---

#### 5. Рекомендации тем (suggest_topics.txt)

**Назначение:** Предложить релевантные темы для изучения

**Промпт:**
```jinja2
Suggest 5-7 relevant topics for the student to study.

Student profile:
- Language: {{ language }}
- Current level: {{ level }}
- Target level: {{ target_level }}
- Goals: {{ goals | join(', ') }}

Consider:
- Topics appropriate for {{ level }} level
- Progression towards {{ target_level }}
- Alignment with goals ({{ goals | join(', ') }})
- Mix of grammar, vocabulary, and practical situations

For each topic provide:
- Name (concise, in Russian)
- Description (1-2 sentences)
- Type (grammar/vocabulary/situation)
- Why it's relevant for this student
- 2-3 example exercises

Respond in JSON format:
{
  "topics": [
    {
      "name": "Pretérito Perfecto",
      "description": "Прошедшее время для недавних действий",
      "type": "grammar",
      "reason": "Essential for {{ level }} level and useful for work communication",
      "examples": ["He trabajado", "Has comido", "Hemos viajado"]
    },
    ...
  ]
}
```

---

#### 6. Извлечение слов из текста (suggest_words.txt)

**Назначение:** Найти слова для добавления в карточки из распознанного текста (OCR)

**Промпт:**
```jinja2
Analyze the following text in {{ language }} and suggest words to add to flashcards.

Text: {{ text }}

Student profile:
- Level: {{ level }}
- Goals: {{ goals | join(', ') }}
- Existing vocabulary: {{ existing_lemmas | join(', ') }}

Requirements:
1. Extract up to 10 most useful words/phrases
2. Prioritize:
   - High-frequency words
   - Words matching student's level
   - Practical vocabulary for their goals
   - Idioms and collocations
3. Exclude:
   - Words already in their deck
   - Too basic for their level
   - Proper nouns (names, places)
4. Include:
   - Single words
   - Common phrases (2-3 words max)

Respond in JSON format:
{
  "suggestions": [
    {
      "word": "empezar",
      "type": "verb",
      "reason": "High-frequency verb for {{ level }}",
      "priority": 1
    },
    ...
  ]
}
```

---

## Обработка ответов LLM

### Парсинг structured output

#### JSON Mode

**OpenAI поддерживает JSON mode:**
```python
response = await openai_client.chat.completions.create(
    model="gpt-4-1106-preview",
    messages=[...],
    response_format={"type": "json_object"},
    temperature=0.7
)

# Парсинг
data = json.loads(response.choices[0].message.content)
```

#### Pydantic Models

**Определяем схемы:**
```python
from pydantic import BaseModel, Field

class CardContent(BaseModel):
    word: str
    lemma: str
    translation: str
    example: str
    example_translation: str
    notes: str | None = None

class ExerciseContent(BaseModel):
    question: str
    prompt: str
    correct_answer: str
    hint: str | None = None
    explanation: str
    alternatives: list[str] = []
    options: list[str] | None = None  # Для multiple choice
    correct_index: int | None = None

class ExerciseResult(BaseModel):
    result: Literal['correct', 'partial', 'incorrect']
    explanation: str
    correct_answer: str
    alternatives: list[str] = []
    feedback: str
    mistakes: list[dict] = []

class TopicSuggestion(BaseModel):
    name: str
    description: str
    type: Literal['grammar', 'vocabulary', 'situation']
    reason: str
    examples: list[str]
```

**Парсинг с валидацией:**
```python
async def parse_llm_response(
    response_text: str,
    model: Type[BaseModel]
) -> BaseModel:
    """
    Парсит и валидирует JSON ответ от LLM.
    """
    try:
        data = json.loads(response_text)
        return model.parse_obj(data)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from LLM: {e}")
        raise LLMParsingError("Invalid JSON response")
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise LLMParsingError(f"Schema validation failed: {e}")
```

---

### Обработка ошибок LLM

#### Типы ошибок

1. **API Errors (OpenAI):**
   - Rate limit exceeded (429)
   - Invalid API key (401)
   - Model overloaded (503)
   - Timeout (408)

2. **Content Errors:**
   - Invalid JSON format
   - Missing required fields
   - Content policy violation (400)

3. **Business Logic Errors:**
   - Generated content doesn't match requirements
   - Hallucinations

#### Retry Strategy

**Экспоненциальный backoff:**
```python
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RateLimitError, ServiceUnavailableError))
)
async def call_llm_with_retry(
    messages: list[dict],
    **kwargs
) -> str:
    """
    Вызывает LLM API с автоматическим retry.
    """
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
    except openai.RateLimitError as e:
        logger.warning(f"Rate limit exceeded, retrying: {e}")
        raise
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise
```

#### Fallback стратегии

**1. Упрощенный промпт:**
```python
async def generate_card_with_fallback(
    word: str,
    profile: LanguageProfile
) -> CardContent:
    """
    Генерирует карточку с fallback на упрощенный промпт.
    """
    try:
        # Попытка с полным промптом
        return await generate_card_content(word, profile)
    except LLMError:
        # Fallback: упрощенный промпт без примеров
        return await generate_card_simple(word, profile)
    except Exception as e:
        # Последний fallback: базовый перевод через словарь API
        logger.error(f"All LLM attempts failed: {e}")
        return await fallback_to_dictionary(word, profile.language)
```

**2. Кэшированные ответы:**
```python
async def get_or_generate_card(
    word: str,
    profile: LanguageProfile
) -> CardContent:
    """
    Пытается получить из кэша, иначе генерирует.
    """
    cache_key = f"card:{profile.language}:{word.lower()}"

    # Проверяем кэш
    cached = await redis.get(cache_key)
    if cached:
        return CardContent.parse_raw(cached)

    # Генерируем
    card = await generate_card_content(word, profile)

    # Кэшируем на 30 дней
    await redis.setex(
        cache_key,
        30 * 24 * 3600,
        card.json()
    )

    return card
```

**3. Graceful degradation:**
```python
async def process_user_message(
    user: User,
    profile: LanguageProfile,
    message: str
) -> BotResponse:
    """
    Обрабатывает сообщение с graceful degradation.
    """
    try:
        # Полная обработка через LLM
        return await process_with_llm(user, profile, message)
    except RateLimitError:
        # Пользователь превысил лимит
        return BotResponse(
            text="Вы достигли дневного лимита сообщений. Попробуйте завтра!",
            show_upgrade=True
        )
    except LLMError:
        # Проблема с LLM сервисом
        return BotResponse(
            text="Извините, сейчас возникли технические проблемы. Попробуйте через минуту.",
            retry_enabled=True
        )
```

---

## Оптимизация

### Кэширование

#### Что кэшировать

**1. Переводы и определения (долгосрочный кэш):**
```python
# Redis TTL: 30 дней
cache_key = f"translation:{source_lang}:{target_lang}:{word}"
```

**2. Сгенерированные карточки:**
```python
# Redis TTL: 30 дней
cache_key = f"card:{language}:{lemma}"
```

**3. Леммы (начальные формы):**
```python
# Redis TTL: бессрочно
cache_key = f"lemma:{language}:{word}"
```

**4. Рекомендации тем (короткий кэш):**
```python
# Redis TTL: 1 час
cache_key = f"topics:{profile_id}"
```

#### Реализация кэширования

**Декоратор для кэширования:**
```python
from functools import wraps
import hashlib

def cache_llm_response(
    ttl: int,
    key_prefix: str,
    key_params: list[str]
):
    """
    Декоратор для кэширования ответов LLM.

    Args:
        ttl: Time to live в секундах
        key_prefix: Префикс ключа кэша
        key_params: Параметры функции для ключа
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Формируем ключ кэша из параметров
            key_values = []
            for param_name in key_params:
                if param_name in kwargs:
                    key_values.append(str(kwargs[param_name]))

            cache_key = f"{key_prefix}:{':'.join(key_values)}"

            # Проверяем кэш
            cached = await redis.get(cache_key)
            if cached:
                logger.info(f"Cache hit: {cache_key}")
                return json.loads(cached)

            # Вызываем функцию
            result = await func(*args, **kwargs)

            # Кэшируем результат
            await redis.setex(
                cache_key,
                ttl,
                json.dumps(result, default=str)
            )

            logger.info(f"Cache miss, stored: {cache_key}")
            return result

        return wrapper
    return decorator

# Использование:
@cache_llm_response(
    ttl=30 * 24 * 3600,  # 30 дней
    key_prefix="card",
    key_params=["language", "word"]
)
async def generate_card_content(
    word: str,
    language: str,
    profile: LanguageProfile
) -> CardContent:
    # ... вызов LLM
    pass
```

#### Стратегия инвалидации

**1. TTL-based (Time To Live):**
- Автоматическое истечение через N секунд
- Подходит для большинства случаев

**2. Manual invalidation:**
```python
async def invalidate_card_cache(word: str, language: str):
    cache_key = f"card:{language}:{word}"
    await redis.delete(cache_key)
```

**3. Cache warming (предзагрузка):**
```python
async def warm_common_cards_cache():
    """
    Предзагружает кэш для частых слов.
    """
    common_words = get_most_common_words()  # Топ 1000 слов

    for language in ['es', 'de', 'fr']:
        for word in common_words:
            try:
                await generate_card_content(word, language, ...)
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed to warm cache for {word}: {e}")
```

---

### Управление токенами

#### Подсчет токенов

**Перед запросом:**
```python
import tiktoken

def count_tokens_for_messages(
    messages: list[dict],
    model: str = "gpt-4"
) -> int:
    """
    Подсчитывает токены для списка сообщений.
    Учитывает служебные токены OpenAI.
    """
    encoding = tiktoken.encoding_for_model(model)

    tokens = 0

    # Служебные токены для каждого сообщения
    tokens_per_message = 3  # <|start|>role<|end|>content<|end|>
    tokens_per_name = 1

    for message in messages:
        tokens += tokens_per_message
        for key, value in message.items():
            tokens += len(encoding.encode(value))
            if key == "name":
                tokens += tokens_per_name

    tokens += 3  # Ответ начинается с <|start|>assistant<|end|>

    return tokens
```

**Мониторинг расхода:**
```python
from dataclasses import dataclass

@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float

async def track_token_usage(
    user_id: str,
    profile_id: str,
    usage: TokenUsage
):
    """
    Отслеживает расход токенов пользователем.
    """
    # Сохраняем в БД
    await db.execute(
        """
        INSERT INTO token_usage (user_id, profile_id, prompt_tokens, completion_tokens, cost, timestamp)
        VALUES (:user_id, :profile_id, :prompt_tokens, :completion_tokens, :cost, NOW())
        """,
        {
            'user_id': user_id,
            'profile_id': profile_id,
            'prompt_tokens': usage.prompt_tokens,
            'completion_tokens': usage.completion_tokens,
            'cost': usage.estimated_cost
        }
    )

    # Обновляем счетчик в Redis
    today = datetime.now().strftime('%Y-%m-%d')
    redis_key = f"tokens:{user_id}:{today}"
    await redis.incrby(redis_key, usage.total_tokens)
    await redis.expire(redis_key, 86400)  # 24 часа
```

#### Оптимизация промптов

**1. Сокращение системного промпта:**
```python
# ❌ Плохо: длинный системный промпт
system_prompt = """
You are a professional language teacher with 20 years of experience...
[500 слов]
"""

# ✅ Хорошо: краткий, но информативный
system_prompt = """
Professional {{ language }} teacher for {{ level }} students.
Focus: clear explanations, practical examples, encouraging feedback.
"""
```

**2. Переиспользование контекста:**
```python
# Вместо передачи полной истории каждый раз,
# используем summarization для старых сообщений

async def compress_old_messages(
    messages: list[ConversationMessage]
) -> str:
    """
    Сжимает старые сообщения в краткое резюме.
    """
    if len(messages) < 10:
        return None

    old_messages = messages[:-10]  # Все кроме последних 10

    summary_prompt = f"""
    Summarize this conversation in 2-3 sentences:

    {format_messages(old_messages)}
    """

    summary = await llm_client.chat(
        messages=[{'role': 'user', 'content': summary_prompt}],
        max_tokens=150
    )

    return summary
```

**3. Ограничение выходных токенов:**
```python
response = await llm_client.chat(
    messages=messages,
    max_tokens=500,  # Ограничиваем длину ответа
    temperature=0.7
)
```

---

### Rate limiting

#### Лимиты (из use-cases.md)

**Бесплатные пользователи:**
- 50 сообщений LLM в день
- 10 упражнений в день
- 200 карточек максимум

**Премиум пользователи:**
- 500 сообщений LLM в день
- Неограниченно упражнений
- Неограниченно карточек

#### Реализация

**Redis-based rate limiting:**
```python
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_limit(
        self,
        user_id: str,
        action: str,
        limit: int,
        window: int = 86400  # 24 часа
    ) -> tuple[bool, int]:
        """
        Проверяет лимит для пользователя.

        Returns:
            (allowed, remaining): разрешено ли действие и сколько осталось
        """
        key = f"ratelimit:{user_id}:{action}:{datetime.now().strftime('%Y-%m-%d')}"

        # Получаем текущий счетчик
        current = await self.redis.get(key)
        current = int(current) if current else 0

        if current >= limit:
            return False, 0

        # Инкрементируем
        await self.redis.incr(key)
        await self.redis.expire(key, window)

        remaining = limit - current - 1
        return True, remaining

    async def get_usage(
        self,
        user_id: str,
        action: str
    ) -> dict:
        """
        Получает информацию об использовании лимита.
        """
        key = f"ratelimit:{user_id}:{action}:{datetime.now().strftime('%Y-%m-%d')}"

        current = await self.redis.get(key)
        current = int(current) if current else 0

        ttl = await self.redis.ttl(key)
        reset_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None

        return {
            'used': current,
            'reset_at': reset_at
        }

# Использование:
rate_limiter = RateLimiter(redis_client)

async def send_llm_message(user: User, message: str):
    # Определяем лимит
    limit = 500 if user.is_premium else 50

    # Проверяем лимит
    allowed, remaining = await rate_limiter.check_limit(
        user_id=user.id,
        action='llm_messages',
        limit=limit
    )

    if not allowed:
        raise RateLimitError(
            "Достигнут дневной лимит сообщений",
            limit=limit,
            reset_at=(datetime.now() + timedelta(days=1)).replace(hour=0, minute=0)
        )

    # Обрабатываем сообщение
    response = await process_with_llm(user, message)

    return response, remaining
```

**Middleware для API:**
```python
from fastapi import Request, HTTPException

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Проверяет rate limits для API запросов.
    """
    user_id = request.state.user.id if hasattr(request.state, 'user') else None

    if not user_id:
        return await call_next(request)

    # Определяем действие по endpoint
    action_map = {
        '/api/cards': 'card_operations',
        '/api/exercises/generate': 'exercises',
        '/api/chat': 'llm_messages'
    }

    action = action_map.get(request.url.path)
    if not action:
        return await call_next(request)

    # Получаем лимит
    user = await get_user(user_id)
    limits = get_user_limits(user)
    limit = limits.get(action, 1000)

    # Проверяем
    allowed, remaining = await rate_limiter.check_limit(user_id, action, limit)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": f"Достигнут лимит: {limit} запросов в день",
                "retry_after": 3600  # через час попробовать снова
            }
        )

    # Добавляем headers
    response = await call_next(request)
    response.headers['X-RateLimit-Limit'] = str(limit)
    response.headers['X-RateLimit-Remaining'] = str(remaining)

    return response
```

---

## Функциональные возможности

### Function calling / Tool use

#### Использование

OpenAI поддерживает function calling для структурированных действий.

**Определение функций:**
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "add_flashcard",
            "description": "Add a word to the user's flashcard deck",
            "parameters": {
                "type": "object",
                "properties": {
                    "word": {
                        "type": "string",
                        "description": "The word to add"
                    },
                    "deck_name": {
                        "type": "string",
                        "description": "Name of the deck (optional)"
                    }
                },
                "required": ["word"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_exercise",
            "description": "Generate a practice exercise for the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Grammar topic or vocabulary theme"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["free_text", "multiple_choice"],
                        "description": "Type of exercise"
                    }
                },
                "required": ["topic"]
            }
        }
    }
]
```

**Вызов LLM с tools:**
```python
async def process_with_tools(
    user: User,
    profile: LanguageProfile,
    message: str,
    history: list
) -> BotResponse:
    """
    Обрабатывает сообщение с поддержкой function calling.
    """
    messages = format_messages_for_llm(
        get_system_prompt(profile),
        history,
        message
    )

    response = await openai_client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=messages,
        tools=tools,
        tool_choice="auto"  # LLM сам решает, вызывать ли функцию
    )

    message = response.choices[0].message

    # Проверяем, есть ли tool calls
    if message.tool_calls:
        # Обрабатываем каждый вызов
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            # Вызываем соответствующую функцию
            if function_name == "add_flashcard":
                result = await add_flashcard(
                    user_id=user.id,
                    profile_id=profile.id,
                    word=arguments['word'],
                    deck_name=arguments.get('deck_name')
                )

                return BotResponse(
                    text=f"Добавил слово '{arguments['word']}' в карточки!",
                    action='card_added',
                    card_id=result.id
                )

            elif function_name == "generate_exercise":
                exercise = await generate_exercise(
                    profile=profile,
                    topic_name=arguments['topic'],
                    exercise_type=arguments.get('type', 'free_text')
                )

                return BotResponse(
                    text="Сгенерировал упражнение для вас:",
                    action='exercise_generated',
                    exercise=exercise
                )

    # Обычный текстовый ответ
    return BotResponse(text=message.content)
```

**Преимущества:**
- LLM сам определяет, когда нужно добавить карточку
- Более естественный диалог
- Меньше промптов для определения намерения

**Недостатки:**
- Дороже (больше токенов)
- Требует GPT-4 (не работает с GPT-3.5-turbo-1106+)

---

### Multimodal (изображения)

#### GPT-4 Vision для OCR

**Использование:**
```python
async def extract_text_from_image(
    image_url: str,
    language: str
) -> str:
    """
    Извлекает текст из изображения через GPT-4 Vision.
    Используется как дополнение к Tesseract OCR для улучшения точности.
    """
    response = await openai_client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Extract all text in {language} from this image. Preserve formatting and structure."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                            "detail": "high"  # для лучшего качества
                        }
                    }
                ]
            }
        ],
        max_tokens=1000
    )

    return response.choices[0].message.content
```

**Комбинированный подход (Tesseract + GPT-4 Vision):**
```python
async def process_image_text(
    image_file: bytes,
    language: str
) -> str:
    """
    Обрабатывает текст с изображения комбинированным методом.
    """
    # 1. Быстрый OCR через Tesseract
    tesseract_text = extract_text_tesseract(image_file, language)

    # 2. Если текст читаемый и длинный - возвращаем
    if len(tesseract_text) > 50 and is_readable(tesseract_text):
        logger.info("Tesseract OCR successful")
        return tesseract_text

    # 3. Если текст плохой или короткий - используем GPT-4 Vision
    logger.info("Falling back to GPT-4 Vision")

    # Загружаем на временный сервер или используем data URI
    image_url = upload_temp_image(image_file)

    vision_text = await extract_text_from_image(image_url, language)

    # Удаляем временный файл
    cleanup_temp_image(image_url)

    return vision_text

def is_readable(text: str) -> bool:
    """
    Проверяет, является ли текст читаемым.
    """
    # Проверяем процент не-ASCII символов
    non_ascii = sum(1 for c in text if ord(c) > 127)
    ratio = non_ascii / len(text) if len(text) > 0 else 0

    # Если > 50% не-ASCII - возможно, мусор
    return ratio < 0.5
```

#### Whisper для голосовых сообщений

**Транскрипция:**
```python
async def transcribe_voice_message(
    audio_file: bytes,
    expected_language: str | None = None
) -> tuple[str, str]:
    """
    Транскрибирует голосовое сообщение через Whisper API.

    Returns:
        (transcript, detected_language)
    """
    # Сохраняем во временный файл (Whisper требует file-like object)
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
        temp_file.write(audio_file)
        temp_file_path = temp_file.name

    try:
        # Транскрибируем
        with open(temp_file_path, 'rb') as audio:
            response = await openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                language=expected_language,  # ISO-639-1 code или None для автоопределения
                response_format="verbose_json"  # Включает detected_language
            )

        transcript = response.text
        detected_language = response.language

        logger.info(f"Transcribed {len(transcript)} chars, language: {detected_language}")

        return transcript, detected_language

    finally:
        # Удаляем временный файл
        os.unlink(temp_file_path)

async def process_voice_message(
    user: User,
    profile: LanguageProfile,
    audio_file: bytes
) -> BotResponse:
    """
    Обрабатывает голосовое сообщение.
    """
    # Транскрибируем
    transcript, detected_language = await transcribe_voice_message(
        audio_file,
        expected_language=profile.language
    )

    # Проверяем соответствие языка
    if detected_language != profile.language:
        logger.warning(
            f"Language mismatch: expected {profile.language}, got {detected_language}"
        )
        # Можно уведомить пользователя или все равно обработать

    # Обрабатываем как текстовое сообщение
    response = await process_user_message(user, profile, transcript)

    # Добавляем информацию о распознавании
    response.metadata = {
        'voice_transcript': transcript,
        'detected_language': detected_language
    }

    return response
```

---

## Интеграция в сервисы

### LLM Service

**Центральный сервис для всех операций с LLM:**

```python
# services/llm_service.py

from openai import AsyncOpenAI
from jinja2 import Environment, FileSystemLoader

class LLMService:
    def __init__(
        self,
        api_key: str,
        redis_client,
        prompts_dir: str = 'prompts'
    ):
        self.client = AsyncOpenAI(api_key=api_key)
        self.redis = redis_client
        self.model = "gpt-4-1106-preview"

        # Jinja2 для промптов
        self.jinja_env = Environment(
            loader=FileSystemLoader(prompts_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def render_prompt(self, template_name: str, context: dict) -> str:
        """Рендерит промпт из шаблона."""
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    async def chat(
        self,
        messages: list[dict],
        response_format: dict | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs
    ) -> str:
        """Базовый метод для chat completion."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        return response.choices[0].message.content

    # === Карточки ===

    async def generate_card(
        self,
        word: str,
        profile: LanguageProfile
    ) -> CardContent:
        """Генерирует содержимое карточки."""
        prompt = self.render_prompt('cards/generate_card.txt', {
            'word': word,
            'language': profile.language,
            'level': profile.current_level,
            'goals': profile.goals
        })

        response = await self.chat(
            messages=[
                {'role': 'system', 'content': get_system_prompt(profile)},
                {'role': 'user', 'content': prompt}
            ],
            response_format={'type': 'json_object'},
            temperature=0.7
        )

        return CardContent.parse_obj(json.loads(response))

    async def get_lemma(self, word: str, language: str) -> str:
        """Определяет лемму слова."""
        prompt = self.render_prompt('utils/get_lemma.txt', {
            'word': word,
            'language': language
        })

        response = await self.chat(
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.0,
            max_tokens=20
        )

        return response.strip()

    # === Упражнения ===

    async def generate_exercise(
        self,
        topic: Topic,
        profile: LanguageProfile,
        exercise_type: str
    ) -> Exercise:
        """Генерирует упражнение."""
        prompt = self.render_prompt('exercises/generate_free_text.txt', {
            'topic_name': topic.name,
            'topic_description': topic.description,
            'topic_type': topic.type,
            'level': profile.current_level,
            'language': profile.language,
            'type': exercise_type
        })

        response = await self.chat(
            messages=[
                {'role': 'system', 'content': get_system_prompt(profile)},
                {'role': 'user', 'content': prompt}
            ],
            response_format={'type': 'json_object'},
            temperature=0.8
        )

        return Exercise.parse_obj(json.loads(response))

    async def check_answer(
        self,
        exercise: Exercise,
        user_answer: str,
        profile: LanguageProfile
    ) -> ExerciseResult:
        """Проверяет ответ на упражнение."""
        prompt = self.render_prompt('exercises/check_answer.txt', {
            'question': exercise.question,
            'prompt': exercise.prompt,
            'correct_answer': exercise.correct_answer,
            'user_answer': user_answer,
            'level': profile.current_level
        })

        response = await self.chat(
            messages=[
                {'role': 'system', 'content': get_system_prompt(profile)},
                {'role': 'user', 'content': prompt}
            ],
            response_format={'type': 'json_object'},
            temperature=0.3
        )

        return ExerciseResult.parse_obj(json.loads(response))

    # === Диалог ===

    async def process_message(
        self,
        user_message: str,
        profile: LanguageProfile,
        history: list[ConversationMessage]
    ) -> str:
        """Обрабатывает сообщение пользователя."""
        messages = format_messages_for_llm(
            get_system_prompt(profile),
            history,
            user_message
        )

        response = await self.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        return response

    # === Мультимодальность ===

    async def extract_text_from_image(
        self,
        image_url: str,
        language: str
    ) -> str:
        """Извлекает текст из изображения."""
        response = await self.client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Extract all {language} text from this image."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url, "detail": "high"}
                        }
                    ]
                }
            ],
            max_tokens=1000
        )

        return response.choices[0].message.content

    async def transcribe_audio(
        self,
        audio_file: bytes,
        language: str | None = None
    ) -> tuple[str, str]:
        """Транскрибирует аудио через Whisper."""
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp:
            temp.write(audio_file)
            temp_path = temp.name

        try:
            with open(temp_path, 'rb') as audio:
                response = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    language=language,
                    response_format="verbose_json"
                )

            return response.text, response.language
        finally:
            os.unlink(temp_path)

# Инициализация
llm_service = LLMService(
    api_key=settings.OPENAI_API_KEY,
    redis_client=redis_client
)
```

---

Этот документ описывает полную работу с LLM в проекте Telegram-бота для изучения языков, включая выбор провайдера, промпт-инжиниринг, обработку ответов, оптимизацию, function calling и мультимодальность.
