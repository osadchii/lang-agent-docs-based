"""Форматирование ответов бота для Telegram."""

from __future__ import annotations

import re
from typing import Sequence

# Telegram message limits
MAX_MESSAGE_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024

# Markdown V2 special characters that need escaping
MARKDOWN_V2_ESCAPE_CHARS = r"_*[]()~`>#+-=|{}.!"


def escape_markdown_v2(text: str) -> str:
    """
    Экранировать специальные символы для Telegram MarkdownV2.

    Args:
        text: Исходный текст

    Returns:
        Текст с экранированными специальными символами

    Example:
        >>> escape_markdown_v2("Hello (world)!")
        'Hello \\(world\\)\\!'
    """
    return re.sub(f"([{re.escape(MARKDOWN_V2_ESCAPE_CHARS)}])", r"\\\1", text)


def format_bold(text: str) -> str:
    """
    Форматировать текст как жирный (MarkdownV2).

    Args:
        text: Текст для форматирования

    Returns:
        Текст в жирном начертании
    """
    escaped = escape_markdown_v2(text)
    return f"*{escaped}*"


def format_italic(text: str) -> str:
    """
    Форматировать текст как курсив (MarkdownV2).

    Args:
        text: Текст для форматирования

    Returns:
        Текст курсивом
    """
    escaped = escape_markdown_v2(text)
    return f"_{escaped}_"


def format_code(text: str) -> str:
    """
    Форматировать текст как код (MarkdownV2).

    Args:
        text: Текст для форматирования

    Returns:
        Текст в моноширинном шрифте
    """
    # В code блоке нужно экранировать только ` и \
    escaped = text.replace("\\", "\\\\").replace("`", "\\`")
    return f"`{escaped}`"


def format_code_block(text: str, language: str = "") -> str:
    """
    Форматировать текст как блок кода (MarkdownV2).

    Args:
        text: Текст для форматирования
        language: Язык программирования для подсветки синтаксиса

    Returns:
        Текст в блоке кода
    """
    # В code block нужно экранировать только ``` и \
    escaped = text.replace("\\", "\\\\").replace("```", "\\`\\`\\`")
    return f"```{language}\n{escaped}\n```"


def format_link(text: str, url: str) -> str:
    """
    Форматировать текст как ссылку (MarkdownV2).

    Args:
        text: Текст ссылки
        url: URL

    Returns:
        Форматированная ссылка
    """
    escaped_text = escape_markdown_v2(text)
    # URL в скобках не нужно экранировать
    return f"[{escaped_text}]({url})"


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """
    Разбить длинное сообщение на части с учетом лимита Telegram.

    Разбивает по параграфам (двойной перевод строки), затем по
    предложениям, и только потом по словам, чтобы сохранить смысл.

    Args:
        text: Исходный текст
        max_length: Максимальная длина одного сообщения

    Returns:
        Список фрагментов текста

    Example:
        >>> long_text = "A" * 5000
        >>> parts = split_message(long_text)
        >>> all(len(p) <= MAX_MESSAGE_LENGTH for p in parts)
        True
    """
    if len(text) <= max_length:
        return [text]

    parts: list[str] = []
    current_part = ""

    # Разбиваем по параграфам (двойной перевод строки)
    paragraphs = text.split("\n\n")

    for paragraph in paragraphs:
        # Если параграф помещается в текущую часть
        if len(current_part) + len(paragraph) + 2 <= max_length:
            if current_part:
                current_part += "\n\n"
            current_part += paragraph
        # Если параграф не помещается, но текущая часть не пустая
        elif current_part:
            parts.append(current_part)
            current_part = paragraph
            # Если параграф сам по себе слишком длинный
            if len(current_part) > max_length:
                split_parts = _split_by_sentences(current_part, max_length)
                parts.extend(split_parts[:-1])
                current_part = split_parts[-1]
        # Если параграф слишком длинный и текущая часть пустая
        else:
            split_parts = _split_by_sentences(paragraph, max_length)
            parts.extend(split_parts[:-1])
            current_part = split_parts[-1]

    # Добавляем последнюю часть
    if current_part:
        parts.append(current_part)

    return parts


def _process_long_sentence(sentence: str, max_length: int) -> tuple[list[str], str]:
    """Обработать слишком длинное предложение."""
    word_parts = _split_by_words(sentence, max_length)
    return word_parts[:-1], word_parts[-1]


def _finalize_sentence_parts(current_part: str, max_length: int) -> list[str]:
    """Завершить обработку частей предложений."""
    if not current_part:
        return []

    if len(current_part) > max_length:
        return _split_by_words(current_part, max_length)

    return [current_part.rstrip()]


def _split_by_sentences(text: str, max_length: int) -> list[str]:
    """Разбить текст по предложениям."""
    if len(text) <= max_length:
        return [text]

    parts: list[str] = []
    current_part = ""

    # Разбиваем по предложениям (. ! ? с пробелом или концом строки)
    sentences = re.split(r"([.!?]\s+)", text)

    # Объединяем предложения с их разделителями
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i]
        delimiter = sentences[i + 1] if i + 1 < len(sentences) else ""
        full_sentence = sentence + delimiter

        if len(current_part) + len(full_sentence) <= max_length:
            current_part += full_sentence
        elif current_part:
            parts.append(current_part.rstrip())
            current_part = full_sentence
            # Если предложение слишком длинное
            if len(current_part) > max_length:
                split_parts, current_part = _process_long_sentence(current_part, max_length)
                parts.extend(split_parts)
        else:
            split_parts, current_part = _process_long_sentence(full_sentence, max_length)
            parts.extend(split_parts)

    # Добавляем последний sentence если он не был добавлен
    if len(sentences) % 2 != 0:
        last_sentence = sentences[-1]
        if len(current_part) + len(last_sentence) <= max_length:
            current_part += last_sentence
        elif current_part:
            parts.append(current_part.rstrip())
            current_part = last_sentence
        else:
            current_part = last_sentence

    # Завершаем обработку
    parts.extend(_finalize_sentence_parts(current_part, max_length))

    return parts


def _split_by_words(text: str, max_length: int) -> list[str]:
    """Разбить текст по словам (последний способ)."""
    if len(text) <= max_length:
        return [text]

    parts: list[str] = []
    current_part = ""
    words = text.split(" ")

    for word in words:
        if len(current_part) + len(word) + 1 <= max_length:
            if current_part:
                current_part += " "
            current_part += word
        elif current_part:
            parts.append(current_part)
            current_part = word
            # Если слово само по себе длиннее лимита, режем его на части
            while len(current_part) > max_length:
                parts.append(current_part[:max_length])
                current_part = current_part[max_length:]
        else:
            # Слово длиннее лимита, режем его на части
            while len(word) > max_length:
                parts.append(word[:max_length])
                word = word[max_length:]
            current_part = word

    if current_part:
        parts.append(current_part)

    return parts


def format_card_response(word: str, translation: str, example: str = "") -> str:
    """
    Форматировать ответ с информацией о карточке.

    Args:
        word: Слово на изучаемом языке
        translation: Перевод
        example: Пример использования (опционально)

    Returns:
        Форматированное сообщение
    """
    parts = [
        format_bold(word) + " — " + escape_markdown_v2(translation),
    ]

    if example:
        parts.append("")
        parts.append(escape_markdown_v2("Пример:"))
        parts.append(format_italic(example))

    return "\n".join(parts)


def format_list(items: Sequence[str], numbered: bool = False) -> str:
    """
    Форматировать список элементов.

    Args:
        items: Список элементов
        numbered: Использовать нумерацию (True) или буллеты (False)

    Returns:
        Форматированный список
    """
    lines: list[str] = []

    for i, item in enumerate(items, start=1):
        prefix = f"{i}\\. " if numbered else "• "
        lines.append(prefix + escape_markdown_v2(item))

    return "\n".join(lines)


def format_error_message(error: str) -> str:
    """
    Форматировать сообщение об ошибке.

    Args:
        error: Текст ошибки

    Returns:
        Форматированное сообщение об ошибке
    """
    return "❌ " + escape_markdown_v2(error)


def format_success_message(message: str) -> str:
    """
    Форматировать сообщение об успехе.

    Args:
        message: Текст сообщения

    Returns:
        Форматированное сообщение об успехе
    """
    return "✅ " + escape_markdown_v2(message)


__all__ = [
    "escape_markdown_v2",
    "format_bold",
    "format_italic",
    "format_code",
    "format_code_block",
    "format_link",
    "split_message",
    "format_card_response",
    "format_list",
    "format_error_message",
    "format_success_message",
    "MAX_MESSAGE_LENGTH",
    "MAX_CAPTION_LENGTH",
]
