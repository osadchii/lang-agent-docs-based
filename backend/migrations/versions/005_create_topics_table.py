"""Create topics table.

Revision ID: 005_create_topics_table
Revises: 004_create_cards_table
Create Date: 2024-11-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql


revision = "005_create_topics_table"
down_revision = "004_create_cards_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "topics",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("profile_id", psql.UUID(as_uuid=True), sa.ForeignKey("language_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "type",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'grammar'"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("is_group", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("owner_id", psql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("exercises_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("partial_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("incorrect_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("accuracy", sa.Numeric(5, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("type IN ('grammar','vocabulary','situation')", name="ck_topics_type"),
    )

    op.create_index(
        "idx_topics_profile_id",
        "topics",
        ["profile_id"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_topics_profile_active",
        "topics",
        ["profile_id", "is_active"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_topics_type",
        "topics",
        ["type"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_topics_is_group",
        "topics",
        ["is_group"],
        postgresql_where=sa.text("deleted = FALSE"),
    )

    op.create_index(
        "idx_topics_one_active_per_profile",
        "topics",
        ["profile_id", "is_active"],
        unique=True,
        postgresql_where=sa.text("is_active = TRUE AND deleted = FALSE"),
    )

    op.execute(
        """
        CREATE TRIGGER update_topics_updated_at
        BEFORE UPDATE ON topics
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_topics_updated_at ON topics")
    op.drop_index("idx_topics_one_active_per_profile", table_name="topics")
    op.drop_index("idx_topics_is_group", table_name="topics")
    op.drop_index("idx_topics_type", table_name="topics")
    op.drop_index("idx_topics_profile_active", table_name="topics")
    op.drop_index("idx_topics_profile_id", table_name="topics")
    op.drop_table("topics")
