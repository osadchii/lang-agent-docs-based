"""Create users table.

Revision ID: 001_create_users_table
Revises: 000_update_updated_at_function
Create Date: 2024-11-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql


revision = "001_create_users_table"
down_revision = "000_update_updated_at_function"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("last_name", sa.String(length=255)),
        sa.Column("username", sa.String(length=255)),
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("premium_expires_at", sa.DateTime()),
        sa.Column("trial_ends_at", sa.DateTime()),
        sa.Column("trial_used", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("timezone", sa.String(length=50), server_default=sa.text("'UTC'")),
        sa.Column("language_code", sa.String(length=10)),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_activity", sa.DateTime()),
    )

    op.create_index(
        "idx_users_telegram_id",
        "users",
        ["telegram_id"],
        unique=True,
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_users_is_premium",
        "users",
        ["is_premium"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "idx_users_last_activity",
        "users",
        ["last_activity"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index("idx_users_created_at", "users", ["created_at"])

    op.execute(
        """
        CREATE TRIGGER update_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_users_updated_at ON users")
    op.drop_index("idx_users_created_at", table_name="users")
    op.drop_index("idx_users_last_activity", table_name="users")
    op.drop_index("idx_users_is_premium", table_name="users")
    op.drop_index("idx_users_telegram_id", table_name="users")
    op.drop_table("users")
