"""Create cards table.

Revision ID: 004_create_cards_table
Revises: 003_create_decks_table
Create Date: 2024-11-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql


revision = "004_create_cards_table"
down_revision = "003_create_decks_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cards",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("deck_id", psql.UUID(as_uuid=True), sa.ForeignKey("decks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word", sa.String(length=200), nullable=False),
        sa.Column("translation", sa.String(length=200), nullable=False),
        sa.Column("example", sa.Text(), nullable=False),
        sa.Column("example_translation", sa.Text(), nullable=False),
        sa.Column("lemma", sa.String(length=200), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'new'"),
        ),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("next_review", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("reviews_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("ease_factor", sa.Numeric(3, 2), nullable=False, server_default=sa.text("2.50")),
        sa.Column("last_rating", sa.String(length=20)),
        sa.Column("last_reviewed_at", sa.DateTime()),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("status IN ('new','learning','review')", name="ck_cards_status"),
        sa.CheckConstraint(
            "last_rating IS NULL OR last_rating IN ('know','repeat','dont_know')",
            name="ck_cards_last_rating",
        ),
    )

    op.create_index(
        "idx_cards_deck_id",
        "cards",
        ["deck_id"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_cards_status",
        "cards",
        ["status"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_cards_next_review",
        "cards",
        ["next_review"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_cards_lemma",
        "cards",
        ["lemma"],
        postgresql_where=sa.text("deleted = FALSE"),
    )

    op.execute(
        """
        CREATE UNIQUE INDEX idx_cards_deck_lemma
        ON cards (deck_id, LOWER(lemma))
        WHERE deleted = FALSE;
        """
    )
    op.execute(
        """
        CREATE INDEX idx_cards_word_search
        ON cards USING gin (to_tsvector('russian', word || ' ' || translation));
        """
    )

    op.execute(
        """
        CREATE TRIGGER update_cards_updated_at
        BEFORE UPDATE ON cards
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_cards_updated_at ON cards")
    op.execute("DROP INDEX IF EXISTS idx_cards_word_search")
    op.execute("DROP INDEX IF EXISTS idx_cards_deck_lemma")
    op.drop_index("idx_cards_lemma", table_name="cards")
    op.drop_index("idx_cards_next_review", table_name="cards")
    op.drop_index("idx_cards_status", table_name="cards")
    op.drop_index("idx_cards_deck_id", table_name="cards")
    op.drop_table("cards")
