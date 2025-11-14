"""Add deck, card, and review tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20251114_000002"
down_revision = "20251110_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    card_status_enum = sa.Enum(
        "new",
        "learning",
        "review",
        name="card_status_enum",
        native_enum=False,
    )
    card_rating_enum = sa.Enum(
        "know",
        "repeat",
        "dont_know",
        name="card_rating_enum",
        native_enum=False,
    )
    card_reviews_rating_enum = sa.Enum(
        "know",
        "repeat",
        "dont_know",
        name="card_reviews_rating_enum",
        native_enum=False,
    )

    bind = op.get_bind()
    card_status_enum.create(bind, checkfirst=True)
    card_rating_enum.create(bind, checkfirst=True)
    card_reviews_rating_enum.create(bind, checkfirst=True)

    op.create_table(
        "decks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_group", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cards_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("new_cards_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("due_cards_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["language_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_decks_profile_id_active",
        "decks",
        ["profile_id"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ix_decks_profile_active_flag",
        "decks",
        ["profile_id", "is_active"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ix_decks_is_group_active",
        "decks",
        ["is_group"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ix_decks_owner_id_active",
        "decks",
        ["owner_id"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ux_decks_active_per_profile",
        "decks",
        ["profile_id"],
        unique=True,
        postgresql_where=sa.text("is_active = TRUE AND deleted = FALSE"),
    )

    op.create_table(
        "cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("deck_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("word", sa.String(length=200), nullable=False),
        sa.Column("translation", sa.String(length=200), nullable=False),
        sa.Column("example", sa.Text(), nullable=False),
        sa.Column("example_translation", sa.Text(), nullable=False),
        sa.Column("lemma", sa.String(length=200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", card_status_enum, nullable=False, server_default=sa.text("'new'")),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "next_review",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column("reviews_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "ease_factor",
            sa.Numeric(3, 2),
            nullable=False,
            server_default=sa.text("2.50"),
        ),
        sa.Column("last_rating", card_rating_enum, nullable=True),
        sa.Column("last_reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("deck_id", "lemma", name="uq_cards_deck_lemma"),
    )
    op.create_index(
        "ix_cards_deck_id_active",
        "cards",
        ["deck_id"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ix_cards_status_active",
        "cards",
        ["status"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ix_cards_next_review_active",
        "cards",
        ["next_review"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ix_cards_lemma_active",
        "cards",
        ["lemma"],
        postgresql_where=sa.text("deleted = FALSE"),
    )

    op.create_table(
        "card_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", card_reviews_rating_enum, nullable=False),
        sa.Column("interval_before", sa.Integer(), nullable=False),
        sa.Column("interval_after", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "reviewed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_card_reviews_card_id", "card_reviews", ["card_id"])
    op.create_index("ix_card_reviews_user_id", "card_reviews", ["user_id"])
    op.create_index("ix_card_reviews_reviewed_at", "card_reviews", ["reviewed_at"])


def downgrade() -> None:
    op.drop_index("ix_card_reviews_reviewed_at", table_name="card_reviews")
    op.drop_index("ix_card_reviews_user_id", table_name="card_reviews")
    op.drop_index("ix_card_reviews_card_id", table_name="card_reviews")
    op.drop_table("card_reviews")

    op.drop_index("ix_cards_lemma_active", table_name="cards")
    op.drop_index("ix_cards_next_review_active", table_name="cards")
    op.drop_index("ix_cards_status_active", table_name="cards")
    op.drop_index("ix_cards_deck_id_active", table_name="cards")
    op.drop_table("cards")

    op.drop_index("ux_decks_active_per_profile", table_name="decks")
    op.drop_index("ix_decks_owner_id_active", table_name="decks")
    op.drop_index("ix_decks_is_group_active", table_name="decks")
    op.drop_index("ix_decks_profile_active_flag", table_name="decks")
    op.drop_index("ix_decks_profile_id_active", table_name="decks")
    op.drop_table("decks")

    bind = op.get_bind()
    sa.Enum(name="card_reviews_rating_enum").drop(bind, checkfirst=True)
    sa.Enum(name="card_rating_enum").drop(bind, checkfirst=True)
    sa.Enum(name="card_status_enum").drop(bind, checkfirst=True)
