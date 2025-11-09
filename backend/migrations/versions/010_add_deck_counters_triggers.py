"""Add deck counter maintenance triggers.

Revision ID: 010_add_deck_counters_triggers
Revises: 009_create_subscriptions_table
Create Date: 2024-11-09
"""

from alembic import op


revision = "010_add_deck_counters_triggers"
down_revision = "009_create_subscriptions_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION refresh_deck_counters(p_deck_id UUID)
        RETURNS VOID AS $$
        BEGIN
            UPDATE decks
            SET
                cards_count = sub.cards_count,
                new_cards_count = sub.new_cards_count,
                due_cards_count = sub.due_cards_count
            FROM (
                SELECT
                    COUNT(*) FILTER (WHERE deleted = FALSE) AS cards_count,
                    COUNT(*) FILTER (WHERE deleted = FALSE AND status = 'new') AS new_cards_count,
                    COUNT(*) FILTER (
                        WHERE deleted = FALSE AND status != 'new' AND next_review <= NOW()
                    ) AS due_cards_count
                FROM cards
                WHERE deck_id = p_deck_id
            ) AS sub
            WHERE decks.id = p_deck_id;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_deck_counters_on_card_change()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                PERFORM refresh_deck_counters(OLD.deck_id);
                RETURN OLD;
            ELSIF TG_OP = 'UPDATE' THEN
                IF NEW.deck_id <> OLD.deck_id THEN
                    PERFORM refresh_deck_counters(OLD.deck_id);
                    PERFORM refresh_deck_counters(NEW.deck_id);
                ELSE
                    PERFORM refresh_deck_counters(NEW.deck_id);
                END IF;
                RETURN NEW;
            ELSE
                PERFORM refresh_deck_counters(NEW.deck_id);
                RETURN NEW;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER update_deck_counters_trigger
        AFTER INSERT OR UPDATE OR DELETE ON cards
        FOR EACH ROW EXECUTE FUNCTION update_deck_counters_on_card_change();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_deck_counters_trigger ON cards")
    op.execute("DROP FUNCTION IF EXISTS update_deck_counters_on_card_change()")
    op.execute("DROP FUNCTION IF EXISTS refresh_deck_counters(UUID)")
