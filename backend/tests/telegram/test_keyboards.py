"""Tests for inline keyboards module."""

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
    """Tests for create_add_to_cards_keyboard."""

    def test_create_keyboard_with_short_word(self) -> None:
        """Test creating keyboard with short word."""
        keyboard = create_add_to_cards_keyboard("casa", "дом")
        assert keyboard.inline_keyboard is not None
        assert len(keyboard.inline_keyboard) == 1
        # Check that button contains text
        button = keyboard.inline_keyboard[0][0]
        assert "Добавить в карточки" in button.text
        assert button.callback_data is not None
        assert button.callback_data.startswith(CALLBACK_ADD_CARD)

    def test_create_keyboard_with_long_word(self) -> None:
        """Test creating keyboard with very long word (>64 bytes)."""
        long_word = "A" * 100
        long_translation = "B" * 100
        keyboard = create_add_to_cards_keyboard(long_word, long_translation)
        # Callback data should be shortened to "add_card:from_message"
        button = keyboard.inline_keyboard[0][0]
        assert button.callback_data is not None
        # Check that callback_data doesn't exceed limit
        assert len(button.callback_data.encode("utf-8")) <= 64


class TestCreateCardActionsKeyboard:
    """Tests for create_card_actions_keyboard."""

    def test_create_keyboard_with_mini_app(self) -> None:
        """Test creating keyboard with Mini App button."""
        card_id = "test-card-id"
        keyboard = create_card_actions_keyboard(card_id, show_mini_app=True)
        # Should have 2 button rows
        assert len(keyboard.inline_keyboard) == 2
        # First row - delete
        delete_button = keyboard.inline_keyboard[0][0]
        assert "Удалить" in delete_button.text
        assert delete_button.callback_data == f"{CALLBACK_REMOVE_CARD}:{card_id}"
        # Second row - Mini App
        mini_app_button = keyboard.inline_keyboard[1][0]
        assert "Mini App" in mini_app_button.text
        assert mini_app_button.web_app is not None

    def test_create_keyboard_without_mini_app(self) -> None:
        """Test creating keyboard without Mini App button."""
        card_id = "test-card-id"
        keyboard = create_card_actions_keyboard(card_id, show_mini_app=False)
        # Should have only 1 row (delete)
        assert len(keyboard.inline_keyboard) == 1


class TestCreateMiniAppButton:
    """Tests for create_mini_app_button."""

    def test_create_button_with_defaults(self) -> None:
        """Test creating button with default parameters."""
        button = create_mini_app_button()
        assert "Mini App" in button.text
        assert button.web_app is not None
        assert "https://" in button.web_app.url

    def test_create_button_with_custom_text(self) -> None:
        """Test creating button with custom text."""
        button = create_mini_app_button(text="Custom Text")
        assert button.text == "Custom Text"

    def test_create_button_with_path(self) -> None:
        """Test creating button with path."""
        button = create_mini_app_button(path="/practice/cards")
        assert button.web_app is not None
        assert "/practice/cards" in button.web_app.url

    def test_create_button_with_params(self) -> None:
        """Test creating button with parameters."""
        params = {"deck_id": "123", "mode": "study"}
        button = create_mini_app_button(params=params)
        assert button.web_app is not None
        url = button.web_app.url
        assert "deck_id=123" in url
        assert "mode=study" in url


class TestCreatePaginationKeyboard:
    """Tests for create_pagination_keyboard."""

    def test_single_page_no_pagination(self) -> None:
        """Test that pagination is not shown for a single page."""
        keyboard = create_pagination_keyboard(1, 1)
        assert len(keyboard.inline_keyboard) == 0

    def test_first_page_pagination(self) -> None:
        """Test pagination on first page."""
        keyboard = create_pagination_keyboard(1, 5)
        # Should have "Next" button
        assert len(keyboard.inline_keyboard) >= 1
        buttons = keyboard.inline_keyboard[0]
        # Check that there's a forward arrow button
        assert any("➡" in btn.text for btn in buttons)
        # Should not have "Prev" button
        assert not any("⬅" in btn.text for btn in buttons)

    def test_middle_page_pagination(self) -> None:
        """Test pagination on middle page."""
        keyboard = create_pagination_keyboard(3, 5)
        buttons = keyboard.inline_keyboard[0]
        # Should have both "Prev" and "Next" buttons
        assert any("⬅" in btn.text for btn in buttons)
        assert any("➡" in btn.text for btn in buttons)

    def test_last_page_pagination(self) -> None:
        """Test pagination on last page."""
        keyboard = create_pagination_keyboard(5, 5)
        buttons = keyboard.inline_keyboard[0]
        # Should have "Prev" button
        assert any("⬅" in btn.text for btn in buttons)
        # Should not have "Next" button
        assert not any("➡" in btn.text for btn in buttons)

    def test_current_page_marked(self) -> None:
        """Test that current page is marked."""
        keyboard = create_pagination_keyboard(3, 5)
        buttons = keyboard.inline_keyboard[0]
        # Current page should be marked with dots
        current_page_button = next((btn for btn in buttons if "· 3 ·" in btn.text), None)
        assert current_page_button is not None

    def test_callback_data_format(self) -> None:
        """Test callback_data format."""
        keyboard = create_pagination_keyboard(2, 5)
        buttons = keyboard.inline_keyboard[0]
        # All buttons should have callback_data with "page:" prefix
        for button in buttons:
            if button.callback_data:
                assert button.callback_data.startswith(CALLBACK_PAGE)


class TestCreateListWithPagination:
    """Tests for create_list_with_pagination."""

    def test_list_without_pagination(self) -> None:
        """Test list without pagination."""
        items = [("Item 1", "item:1"), ("Item 2", "item:2")]
        keyboard = create_list_with_pagination(items, 1, items_per_page=5)
        # Should have 2 buttons (without pagination)
        assert len(keyboard.inline_keyboard) == 2

    def test_list_with_pagination(self) -> None:
        """Test list with pagination."""
        items = [(f"Item {i}", f"item:{i}") for i in range(20)]
        keyboard = create_list_with_pagination(items, 1, items_per_page=5)
        # Should have 5 item buttons + pagination rows
        # Count buttons with "Item" in text
        item_buttons = [row[0] for row in keyboard.inline_keyboard if row and "Item" in row[0].text]
        assert len(item_buttons) == 5

    def test_list_pagination_page_2(self) -> None:
        """Test second page of list."""
        items = [(f"Item {i}", f"item:{i}") for i in range(1, 21)]
        keyboard = create_list_with_pagination(items, 2, items_per_page=5)
        # Second page should have Item 6-10
        item_buttons = [row[0] for row in keyboard.inline_keyboard if row and "Item" in row[0].text]
        # Check that first button is Item 6
        assert "Item 6" in item_buttons[0].text


class TestCreateConfirmationKeyboard:
    """Tests for create_confirmation_keyboard."""

    def test_create_confirmation_keyboard(self) -> None:
        """Test creating confirmation keyboard."""
        keyboard = create_confirmation_keyboard("confirm:action")
        # Should have 1 row with 2 buttons
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 2
        # First button - confirmation
        confirm_btn = keyboard.inline_keyboard[0][0]
        assert "Подтвердить" in confirm_btn.text
        assert confirm_btn.callback_data == "confirm:action"
        # Second button - cancel
        cancel_btn = keyboard.inline_keyboard[0][1]
        assert "Отмена" in cancel_btn.text
        assert cancel_btn.callback_data == CALLBACK_CANCEL


class TestRemoveKeyboard:
    """Tests for remove_keyboard."""

    def test_remove_keyboard(self) -> None:
        """Test creating empty keyboard."""
        keyboard = remove_keyboard()
        assert keyboard.inline_keyboard is not None
        assert len(keyboard.inline_keyboard) == 0
