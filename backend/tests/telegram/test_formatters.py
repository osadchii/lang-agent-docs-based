"""Тесты для модуля форматирования ответов бота."""

from __future__ import annotations

from app.telegram.formatters import (
    MAX_MESSAGE_LENGTH,
    escape_markdown,
    escape_markdown_v2,
    format_bold,
    format_card_response,
    format_code,
    format_code_block,
    format_error_message,
    format_italic,
    format_link,
    format_list,
    format_success_message,
    split_message,
)


class TestEscapeMarkdown:
    """Тесты для escape_markdown (legacy mode для LLM ответов)."""

    def test_escape_backticks(self) -> None:
        """Тест экранирования backticks."""
        text = "Code: `print('hello')`"
        result = escape_markdown(text)
        assert result == r"Code: \`print('hello')\`"

    def test_preserve_markdown_formatting(self) -> None:
        """Тест что Markdown форматирование сохраняется."""
        text = "*bold* and _italic_ text"
        result = escape_markdown(text)
        # * и _ НЕ экранируются - это часть Markdown форматирования от LLM
        assert result == "*bold* and _italic_ text"

    def test_no_escape_for_regular_text(self) -> None:
        """Тест что обычный текст не изменяется."""
        text = "Hello world 123"
        result = escape_markdown(text)
        assert result == text


class TestEscapeMarkdownV2:
    """Тесты для escape_markdown_v2."""

    def test_escape_special_characters(self) -> None:
        """Тест экранирования специальных символов."""
        text = "Hello (world)!"
        result = escape_markdown_v2(text)
        assert result == r"Hello \(world\)\!"

    def test_escape_all_special_chars(self) -> None:
        """Тест экранирования всех спецсимволов MarkdownV2."""
        text = "_*[]()~`>#+-=|{}.!"
        result = escape_markdown_v2(text)
        # Все символы должны быть экранированы
        assert "\\" in result
        for char in text:
            assert f"\\{char}" in result

    def test_no_escape_for_regular_text(self) -> None:
        """Тест что обычный текст не изменяется."""
        text = "Hello world 123"
        result = escape_markdown_v2(text)
        # Буквы, цифры и пробелы не экранируются
        assert "Hello" in result
        assert "world" in result
        assert "123" in result


class TestFormatBold:
    """Тесты для format_bold."""

    def test_format_simple_text(self) -> None:
        """Тест форматирования простого текста."""
        text = "Hello"
        result = format_bold(text)
        assert result == "*Hello*"

    def test_format_text_with_special_chars(self) -> None:
        """Тест форматирования текста со спецсимволами."""
        text = "Hello (world)!"
        result = format_bold(text)
        # Спецсимволы должны быть экранированы внутри *...*
        assert result.startswith("*")
        assert result.endswith("*")
        assert r"\(" in result
        assert r"\)" in result


class TestFormatItalic:
    """Тесты для format_italic."""

    def test_format_simple_text(self) -> None:
        """Тест форматирования простого текста."""
        text = "Hello"
        result = format_italic(text)
        assert result == "_Hello_"

    def test_format_text_with_underscore(self) -> None:
        """Тест форматирования текста с подчеркиванием."""
        text = "hello_world"
        result = format_italic(text)
        # Подчеркивание должно быть экранировано
        assert r"\_" in result


class TestFormatCode:
    """Тесты для format_code."""

    def test_format_simple_code(self) -> None:
        """Тест форматирования простого кода."""
        code = "print('hello')"
        result = format_code(code)
        assert result == "`print('hello')`"

    def test_format_code_with_backtick(self) -> None:
        """Тест форматирования кода с обратными кавычками."""
        code = "print(`hello`)"
        result = format_code(code)
        # Обратные кавычки должны быть экранированы
        assert r"\`" in result


class TestFormatCodeBlock:
    """Тесты для format_code_block."""

    def test_format_code_block_without_language(self) -> None:
        """Тест форматирования блока кода без языка."""
        code = "print('hello')"
        result = format_code_block(code)
        assert result.startswith("```")
        assert result.endswith("```")
        assert "print('hello')" in result

    def test_format_code_block_with_language(self) -> None:
        """Тест форматирования блока кода с языком."""
        code = "print('hello')"
        result = format_code_block(code, language="python")
        assert result.startswith("```python")
        assert result.endswith("```")


class TestFormatLink:
    """Тесты для format_link."""

    def test_format_simple_link(self) -> None:
        """Тест форматирования простой ссылки."""
        text = "Click here"
        url = "https://example.com"
        result = format_link(text, url)
        assert result == "[Click here](https://example.com)"

    def test_format_link_with_special_chars_in_text(self) -> None:
        """Тест форматирования ссылки со спецсимволами в тексте."""
        text = "Click (here)!"
        url = "https://example.com"
        result = format_link(text, url)
        # Спецсимволы в тексте должны быть экранированы
        assert r"\(" in result
        assert r"\)" in result
        # URL не экранируется
        assert "(https://example.com)" in result


class TestSplitMessage:
    """Тесты для split_message."""

    def test_short_message_not_split(self) -> None:
        """Тест что короткое сообщение не разбивается."""
        text = "Short message"
        result = split_message(text)
        assert len(result) == 1
        assert result[0] == text

    def test_long_message_split(self) -> None:
        """Тест что длинное сообщение разбивается."""
        text = "A" * (MAX_MESSAGE_LENGTH + 100)
        result = split_message(text)
        assert len(result) > 1
        # Каждая часть должна быть <= MAX_MESSAGE_LENGTH
        for part in result:
            assert len(part) <= MAX_MESSAGE_LENGTH

    def test_split_by_paragraphs(self) -> None:
        """Тест разбиения по параграфам."""
        text = "Paragraph 1\n\nParagraph 2\n\nParagraph 3"
        result = split_message(text, max_length=20)
        # Должно быть минимум 2 части (т.к. не помещается в 20 символов)
        assert len(result) >= 2

    def test_split_preserves_content(self) -> None:
        """Тест что разбиение сохраняет весь контент."""
        text = "A" * (MAX_MESSAGE_LENGTH + 100)
        result = split_message(text)
        # Объединенные части должны давать исходный текст
        joined = "".join(result)
        assert joined == text


class TestFormatCardResponse:
    """Тесты для format_card_response."""

    def test_format_card_without_example(self) -> None:
        """Тест форматирования карточки без примера."""
        result = format_card_response("casa", "дом")
        assert "*casa*" in result
        assert "дом" in result

    def test_format_card_with_example(self) -> None:
        """Тест форматирования карточки с примером."""
        result = format_card_response("casa", "дом", "Mi casa es tu casa")
        assert "*casa*" in result
        assert "дом" in result
        assert "Пример" in result
        assert "Mi casa es tu casa" in result


class TestFormatList:
    """Тесты для format_list."""

    def test_format_bullet_list(self) -> None:
        """Тест форматирования списка с буллетами."""
        items = ["Item 1", "Item 2", "Item 3"]
        result = format_list(items, numbered=False)
        assert "• Item 1" in result
        assert "• Item 2" in result
        assert "• Item 3" in result

    def test_format_numbered_list(self) -> None:
        """Тест форматирования нумерованного списка."""
        items = ["First", "Second", "Third"]
        result = format_list(items, numbered=True)
        # Числа экранируются как 1\.
        assert r"1\. First" in result
        assert r"2\. Second" in result
        assert r"3\. Third" in result

    def test_format_empty_list(self) -> None:
        """Тест форматирования пустого списка."""
        items: list[str] = []
        result = format_list(items)
        assert result == ""


class TestFormatMessages:
    """Тесты для format_error_message и format_success_message."""

    def test_format_error_message(self) -> None:
        """Тест форматирования сообщения об ошибке."""
        result = format_error_message("Something went wrong")
        assert result.startswith("❌")
        assert "Something went wrong" in result

    def test_format_success_message(self) -> None:
        """Тест форматирования сообщения об успехе."""
        result = format_success_message("Operation completed")
        assert result.startswith("✅")
        assert "Operation completed" in result

    def test_format_error_with_special_chars(self) -> None:
        """Тест форматирования ошибки со спецсимволами."""
        result = format_error_message("Error (code 404)!")
        # Спецсимволы должны быть экранированы
        assert r"\(" in result
        assert r"\)" in result
        assert r"\!" in result


class TestSplitMessageEdgeCases:
    """Дополнительные тесты для граничных случаев split_message."""

    def test_split_message_with_paragraphs_and_long_paragraph(self) -> None:
        """Тест разбиения с параграфами где один параграф слишком длинный."""
        # Создаем текст с нормальными параграфами и одним огромным
        short_para = "Short paragraph.\n\n"
        long_para = "A" * (MAX_MESSAGE_LENGTH + 100)
        text = short_para + long_para

        result = split_message(text)

        # Должно быть минимум 2 части
        assert len(result) >= 2
        # Первая часть должна содержать короткий параграф
        assert "Short paragraph" in result[0]
        # Все части должны быть в пределах лимита
        for part in result:
            assert len(part) <= MAX_MESSAGE_LENGTH

    def test_split_message_single_long_word(self) -> None:
        """Тест разбиения сообщения с одним очень длинным словом."""
        # Одно слово длиннее лимита
        long_word = "B" * (MAX_MESSAGE_LENGTH + 500)
        result = split_message(long_word)

        # Должно быть разбито на части
        assert len(result) >= 2
        # Все части должны быть в пределах лимита
        for part in result:
            assert len(part) <= MAX_MESSAGE_LENGTH
        # Объединенное должно дать исходное слово
        assert "".join(result) == long_word

    def test_split_by_sentences_with_long_sentence(self) -> None:
        """Тест разбиения текста с очень длинным предложением."""
        # Создаем несколько нормальных предложений и одно очень длинное
        normal = "This is a short sentence. Another short one. "
        long_sentence = "C" * (MAX_MESSAGE_LENGTH + 100) + ". "
        text = normal + long_sentence + "Final sentence."

        result = split_message(text)

        # Должно быть минимум 2 части
        assert len(result) >= 2
        # Все части должны быть в пределах лимита
        for part in result:
            assert len(part) <= MAX_MESSAGE_LENGTH

    def test_split_preserves_multiple_paragraphs(self) -> None:
        """Тест что разбиение сохраняет структуру параграфов."""
        para1 = "First paragraph with some text.\n\n"
        para2 = "Second paragraph with more text.\n\n"
        para3 = "Third paragraph here."
        text = para1 + para2 + para3

        result = split_message(text, max_length=100)

        # Должно быть разбито
        assert len(result) >= 1
        # Объединенное должно совпадать с исходным
        joined = "".join(result)
        assert joined == text

    def test_split_message_exactly_at_limit(self) -> None:
        """Тест разбиения сообщения ровно по лимиту."""
        # Создаем текст ровно MAX_MESSAGE_LENGTH
        text = "D" * MAX_MESSAGE_LENGTH
        result = split_message(text)

        # Не должно разбиваться
        assert len(result) == 1
        assert result[0] == text

    def test_split_message_one_char_over_limit(self) -> None:
        """Тест разбиения сообщения на 1 символ больше лимита."""
        text = "E" * (MAX_MESSAGE_LENGTH + 1)
        result = split_message(text)

        # Должно разбиться на 2 части
        assert len(result) == 2
        assert len(result[0]) == MAX_MESSAGE_LENGTH
        assert len(result[1]) == 1
