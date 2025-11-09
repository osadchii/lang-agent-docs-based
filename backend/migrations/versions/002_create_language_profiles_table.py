"""Create language_profiles table.

Revision ID: 002_create_language_profiles_table
Revises: 001_create_users_table
Create Date: 2024-11-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql


revision = "002_create_language_profiles_table"
down_revision = "001_create_users_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "language_profiles",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", psql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("language_name", sa.String(length=100), nullable=False),
        sa.Column("current_level", sa.String(length=2), nullable=False),
        sa.Column("target_level", sa.String(length=2), nullable=False),
        sa.Column("goals", psql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("interface_language", sa.String(length=10), nullable=False, server_default=sa.text("'ru'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("streak", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("best_streak", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_active_days", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_activity_date", sa.Date()),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("current_level IN ('A1','A2','B1','B2','C1','C2')", name="ck_language_profiles_current_level"),
        sa.CheckConstraint("target_level IN ('A1','A2','B1','B2','C1','C2')", name="ck_language_profiles_target_level"),
        sa.CheckConstraint(
            "CASE target_level "
            "WHEN 'A1' THEN current_level = 'A1' "
            "WHEN 'A2' THEN current_level IN ('A1','A2') "
            "WHEN 'B1' THEN current_level IN ('A1','A2','B1') "
            "WHEN 'B2' THEN current_level IN ('A1','A2','B1','B2') "
            "WHEN 'C1' THEN current_level IN ('A1','A2','B1','B2','C1') "
            "ELSE TRUE END",
            name="ck_language_profiles_target_not_lower",
        ),
    )

    op.create_index(
        "idx_profiles_user_id",
        "language_profiles",
        ["user_id"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_profiles_user_active",
        "language_profiles",
        ["user_id", "is_active"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_profiles_language",
        "language_profiles",
        ["language"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_profiles_last_activity",
        "language_profiles",
        ["last_activity_date"],
        postgresql_where=sa.text("deleted = FALSE"),
    )

    op.create_index(
        "idx_profiles_user_language",
        "language_profiles",
        ["user_id", "language"],
        unique=True,
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_profiles_one_active_per_user",
        "language_profiles",
        ["user_id", "is_active"],
        unique=True,
        postgresql_where=sa.text("is_active = TRUE AND deleted = FALSE"),
    )

    op.execute(
        """
        CREATE TRIGGER update_profiles_updated_at
        BEFORE UPDATE ON language_profiles
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_profiles_updated_at ON language_profiles")
    op.drop_index("idx_profiles_one_active_per_user", table_name="language_profiles")
    op.drop_index("idx_profiles_user_language", table_name="language_profiles")
    op.drop_index("idx_profiles_last_activity", table_name="language_profiles")
    op.drop_index("idx_profiles_language", table_name="language_profiles")
    op.drop_index("idx_profiles_user_active", table_name="language_profiles")
    op.drop_index("idx_profiles_user_id", table_name="language_profiles")
    op.drop_table("language_profiles")
