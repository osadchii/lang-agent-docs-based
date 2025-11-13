"""Тесты для модуля inline-клавиатур."""

from __future__ import annotations

from app.telegram.keyboards import (
    CALLBACK_ADD_CARD,
    CALLBACK_CANCEL,
    CALLBACK_PAGE,
    CALLBACK_REMOVE_CARD,
    create_add_to_cards_keyboard,
    create_card_actions_keyboard,
    create_confirmation_keyboard,
    create_list_with_pagination,
    create_mini_app_button,
    create_pagination_keyboard,
    remove_keyboard,
)


class TestCreateAddToCardsKeyboard:
    """Тесты для create_add_to_cards_keyboard."""

    def test_create_keyboard_with_short_word(self) -> None:
        """Тест создания клавиатуры с коротким словом."""
        keyboard = create_add_to_cards_keyboard("casa", "дом")
        assert keyboard.inline_keyboard is not None
        assert len(keyboard.inline_keyboard) == 1
        # Проверяем что кнопка содержит текст
        button = keyboard.inline_keyboard[0][0]
        assert "Добавить в карточки" in button.text
        assert button.callback_data is not None
        assert button.callback_data.startswith(CALLBACK_ADD_CARD)

    def test_create_keyboard_with_long_word(self) -> None:
        """Тест создания клавиатуры с очень длинным словом (>64 байт)."""
        long_word = "A" * 100
        long_translation = "B" * 100
        keyboard = create_add_to_cards_keyboard(long_word, long_translation)
        # Callback data должен быть укорочен до "add_card:from_message"
        button = keyboard.inline_keyboard[0][0]
        assert button.callback_data is not None
        # Проверяем что callback_data не превышает лимит
        assert len(button.callback_data.encode("utf-8")) <= 64


class TestCreateCardActionsKeyboard:
    """Тесты для create_card_actions_keyboard."""

    def test_create_keyboard_with_mini_app(self) -> None:
        """Тест создания клавиатуры с кнопкой Mini App."""
        card_id = "test-card-id"
        keyboard = create_card_actions_keyboard(card_id, show_mini_app=True)
        # Должно быть 2 ряда кнопок
        assert len(keyboard.inline_keyboard) == 2
        # Первый ряд - удаление
        delete_button = keyboard.inline_keyboard[0][0]
        assert "Удалить" in delete_button.text
        assert delete_button.callback_data == f"{CALLBACK_REMOVE_CARD}:{card_id}"
        # Второй ряд - Mini App
        mini_app_button = keyboard.inline_keyboard[1][0]
        assert "Mini App" in mini_app_button.text
        assert mini_app_button.web_app is not None

    def test_create_keyboard_without_mini_app(self) -> None:
        """Тест создания клавиатуры без кнопки Mini App."""
        card_id = "test-card-id"
        keyboard = create_card_actions_keyboard(card_id, show_mini_app=False)
        # Должен быть только 1 ряд (удаление)
        assert len(keyboard.inline_keyboard) == 1


class TestCreateMiniAppButton:
    """Тесты для create_mini_app_button."""

    def test_create_button_with_defaults(self) -> None:
        """Тест создания кнопки с дефолтными параметрами."""
        button = create_mini_app_button()
        assert "Mini App" in button.text
        assert button.web_app is not None
        assert "https://" in button.web_app.url

    def test_create_button_with_custom_text(self) -> None:
        """Тест создания кнопки с кастомным текстом."""
        button = create_mini_app_button(text="Custom Text")
        assert button.text == "Custom Text"

    def test_create_button_with_path(self) -> None:
        """Тест создания кнопки с путем."""
        button = create_mini_app_button(path="/practice/cards")
        assert button.web_app is not None
        assert "/practice/cards" in button.web_app.url

    def test_create_button_with_params(self) -> None:
        """Тест создания кнопки с параметрами."""
        params = {"deck_id": "123", "mode": "study"}
        button = create_mini_app_button(params=params)
        assert button.web_app is not None
        url = button.web_app.url
        assert "deck_id=123" in url
        assert "mode=study" in url


class TestCreatePaginationKeyboard:
    """Тесты для create_pagination_keyboard."""

    def test_single_page_no_pagination(self) -> None:
        """Тест что для одной страницы пагинация не показывается."""
        keyboard = create_pagination_keyboard(1, 1)
        assert len(keyboard.inline_keyboard) == 0

    def test_first_page_pagination(self) -> None:
        """Тест пагинации на первой странице."""
        keyboard = create_pagination_keyboard(1, 5)
        # Должна быть кнопка "След"
        assert len(keyboard.inline_keyboard) >= 1
        buttons = keyboard.inline_keyboard[0]
        # Проверяем что есть кнопка со стрелкой вперед
        assert any("➡" in btn.text for btn in buttons)
        # Не должно быть кнопки "Пред"
        assert not any("⬅" in btn.text for btn in buttons)

    def test_middle_page_pagination(self) -> None:
        """Тест пагинации на средней странице."""
        keyboard = create_pagination_keyboard(3, 5)
        buttons = keyboard.inline_keyboard[0]
        # Должны быть обе кнопки: "Пред" и "След"
        assert any("⬅" in btn.text for btn in buttons)
        assert any("➡" in btn.text for btn in buttons)

    def test_last_page_pagination(self) -> None:
        """Тест пагинации на последней странице."""
        keyboard = create_pagination_keyboard(5, 5)
        buttons = keyboard.inline_keyboard[0]
        # Должна быть кнопка "Пред"
        assert any("⬅" in btn.text for btn in buttons)
        # Не должно быть кнопки "След"
        assert not any("➡" in btn.text for btn in buttons)

    def test_current_page_marked(self) -> None:
        """Тест что текущая страница отмечена."""
        keyboard = create_pagination_keyboard(3, 5)
        buttons = keyboard.inline_keyboard[0]
        # Текущая страница должна быть с точками
        current_page_button = next((btn for btn in buttons if "· 3 ·" in btn.text), None)
        assert current_page_button is not None

    def test_callback_data_format(self) -> None:
        """Тест формата callback_data."""
        keyboard = create_pagination_keyboard(2, 5)
        buttons = keyboard.inline_keyboard[0]
        # Все кнопки должны иметь callback_data с префиксом "page:"
        for button in buttons:
            if button.callback_data:
                assert button.callback_data.startswith(CALLBACK_PAGE)


class TestCreateListWithPagination:
    """Тесты для create_list_with_pagination."""

    def test_list_without_pagination(self) -> None:
        """Тест списка без пагинации."""
        items = [("Item 1", "item:1"), ("Item 2", "item:2")]
        keyboard = create_list_with_pagination(items, 1, items_per_page=5)
        # Должно быть 2 кнопки (без пагинации)
        assert len(keyboard.inline_keyboard) == 2

    def test_list_with_pagination(self) -> None:
        """Тест списка с пагинацией."""
        items = [(f"Item {i}", f"item:{i}") for i in range(20)]
        keyboard = create_list_with_pagination(items, 1, items_per_page=5)
        # Должно быть 5 кнопок с элементами + ряды пагинации
        # Считаем кнопки с "Item" в тексте
        item_buttons = [row[0] for row in keyboard.inline_keyboard if row and "Item" in row[0].text]
        assert len(item_buttons) == 5

    def test_list_pagination_page_2(self) -> None:
        """Тест второй страницы списка."""
        items = [(f"Item {i}", f"item:{i}") for i in range(1, 21)]
        keyboard = create_list_with_pagination(items, 2, items_per_page=5)
        # На второй странице должны быть Item 6-10
        item_buttons = [row[0] for row in keyboard.inline_keyboard if row and "Item" in row[0].text]
        # Проверяем что первая кнопка - Item 6
        assert "Item 6" in item_buttons[0].text


class TestCreateConfirmationKeyboard:
    """Тесты для create_confirmation_keyboard."""

    def test_create_confirmation_keyboard(self) -> None:
        """Тест создания клавиатуры подтверждения."""
        keyboard = create_confirmation_keyboard("confirm:action")
        # Должен быть 1 ряд с 2 кнопками
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 2
        # Первая кнопка - подтверждение
        confirm_btn = keyboard.inline_keyboard[0][0]
        assert "Подтвердить" in confirm_btn.text
        assert confirm_btn.callback_data == "confirm:action"
        # Вторая кнопка - отмена
        cancel_btn = keyboard.inline_keyboard[0][1]
        assert "Отмена" in cancel_btn.text
        assert cancel_btn.callback_data == CALLBACK_CANCEL


class TestRemoveKeyboard:
    """Тесты для remove_keyboard."""

    def test_remove_keyboard(self) -> None:
        """Тест создания пустой клавиатуры."""
        keyboard = remove_keyboard()
        assert keyboard.inline_keyboard is not None
        assert len(keyboard.inline_keyboard) == 0
