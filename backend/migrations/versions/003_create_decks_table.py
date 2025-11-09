"""Create decks table.

Revision ID: 003_create_decks_table
Revises: 002_create_language_profiles_table
Create Date: 2024-11-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql


revision = "003_create_decks_table"
down_revision = "002_create_language_profiles_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decks",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("profile_id", psql.UUID(as_uuid=True), sa.ForeignKey("language_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("is_group", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("owner_id", psql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("cards_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("new_cards_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("due_cards_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index(
        "idx_decks_profile_id",
        "decks",
        ["profile_id"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_decks_profile_active",
        "decks",
        ["profile_id", "is_active"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_decks_is_group",
        "decks",
        ["is_group"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_decks_owner_id",
        "decks",
        ["owner_id"],
        postgresql_where=sa.text("deleted = FALSE"),
    )

    op.create_index(
        "idx_decks_one_active_per_profile",
        "decks",
        ["profile_id", "is_active"],
        unique=True,
        postgresql_where=sa.text("is_active = TRUE AND deleted = FALSE"),
    )

    op.execute(
        """
        CREATE TRIGGER update_decks_updated_at
        BEFORE UPDATE ON decks
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_decks_updated_at ON decks")
    op.drop_index("idx_decks_one_active_per_profile", table_name="decks")
    op.drop_index("idx_decks_owner_id", table_name="decks")
    op.drop_index("idx_decks_is_group", table_name="decks")
    op.drop_index("idx_decks_profile_active", table_name="decks")
    op.drop_index("idx_decks_profile_id", table_name="decks")
    op.drop_table("decks")
