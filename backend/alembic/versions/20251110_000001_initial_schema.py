"""Initial schema with users, language profiles, and conversation history."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20251110_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("premium_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("trial_ends_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("trial_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "timezone", sa.String(length=50), nullable=False, server_default=sa.text("'UTC'")
        ),
        sa.Column("language_code", sa.String(length=10), nullable=True),
        sa.Column("last_activity", sa.TIMESTAMP(timezone=True), nullable=True),
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
    )
    op.create_index(
        "ux_users_telegram_id_active",
        "users",
        ["telegram_id"],
        unique=True,
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ix_users_is_premium_active",
        "users",
        ["is_premium"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ix_users_last_activity_active",
        "users",
        ["last_activity"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index("ix_users_created_at", "users", ["created_at"])

    op.create_table(
        "language_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("language_name", sa.String(length=100), nullable=False),
        sa.Column("current_level", sa.String(length=2), nullable=False),
        sa.Column("target_level", sa.String(length=2), nullable=False),
        sa.Column(
            "goals",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "interface_language",
            sa.String(length=10),
            nullable=False,
            server_default=sa.text("'ru'"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("streak", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("best_streak", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_active_days", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_activity_date", sa.Date(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "current_level IN ('A1','A2','B1','B2','C1','C2')",
            name="ck_language_profiles_current_level",
        ),
        sa.CheckConstraint(
            "target_level IN ('A1','A2','B1','B2','C1','C2')",
            name="ck_language_profiles_target_level",
        ),
        sa.CheckConstraint(
            """
            CASE target_level
                WHEN 'A1' THEN current_level = 'A1'
                WHEN 'A2' THEN current_level IN ('A1','A2')
                WHEN 'B1' THEN current_level IN ('A1','A2','B1')
                WHEN 'B2' THEN current_level IN ('A1','A2','B1','B2')
                WHEN 'C1' THEN current_level IN ('A1','A2','B1','B2','C1')
                ELSE TRUE
            END
            """,
            name="ck_language_profiles_valid_target_level",
        ),
    )
    op.create_index(
        "ix_language_profiles_user_id_active",
        "language_profiles",
        ["user_id"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ix_language_profiles_user_active_flag",
        "language_profiles",
        ["user_id", "is_active"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ix_language_profiles_language_active",
        "language_profiles",
        ["language"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ix_language_profiles_last_activity",
        "language_profiles",
        ["last_activity_date"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ux_language_profiles_user_language_active",
        "language_profiles",
        ["user_id", "language"],
        unique=True,
        postgresql_where=sa.text("deleted = FALSE"),
    )

    message_role_enum = sa.Enum(
        "user",
        "assistant",
        "system",
        name="message_role_enum",
        native_enum=False,
    )
    message_role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "conversation_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", message_role_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["language_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_conversation_history_user_profile",
        "conversation_history",
        ["user_id", "profile_id"],
    )
    op.create_index(
        "ix_conversation_history_timestamp",
        "conversation_history",
        ["timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_history_timestamp", table_name="conversation_history")
    op.drop_index("ix_conversation_history_user_profile", table_name="conversation_history")
    op.drop_table("conversation_history")
    sa.Enum(name="message_role_enum").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ux_language_profiles_user_language_active", table_name="language_profiles")
    op.drop_index("ix_language_profiles_last_activity", table_name="language_profiles")
    op.drop_index("ix_language_profiles_language_active", table_name="language_profiles")
    op.drop_index("ix_language_profiles_user_active_flag", table_name="language_profiles")
    op.drop_index("ix_language_profiles_user_id_active", table_name="language_profiles")
    op.drop_table("language_profiles")

    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_index("ix_users_last_activity_active", table_name="users")
    op.drop_index("ix_users_is_premium_active", table_name="users")
    op.drop_index("ux_users_telegram_id_active", table_name="users")
    op.drop_table("users")
