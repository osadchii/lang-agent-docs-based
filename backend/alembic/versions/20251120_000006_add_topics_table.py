"""Add topics table for exercise grouping."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20251120_000006"
down_revision = "20251119_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    topic_type_enum = sa.Enum(
        "grammar",
        "vocabulary",
        "situation",
        name="topic_type_enum",
        native_enum=False,
    )
    bind = op.get_bind()
    topic_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", topic_type_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_group", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("exercises_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("partial_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("incorrect_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "accuracy",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
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
        "ix_topics_profile_id_active",
        "topics",
        ["profile_id"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ix_topics_profile_active_flag",
        "topics",
        ["profile_id", "is_active"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ix_topics_type_active",
        "topics",
        ["type"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ix_topics_is_group_active",
        "topics",
        ["is_group"],
        postgresql_where=sa.text("deleted = FALSE"),
    )
    op.create_index(
        "ux_topics_active_per_profile",
        "topics",
        ["profile_id"],
        unique=True,
        postgresql_where=sa.text("is_active = TRUE AND deleted = FALSE"),
    )


def downgrade() -> None:
    op.drop_index("ux_topics_active_per_profile", table_name="topics")
    op.drop_index("ix_topics_is_group_active", table_name="topics")
    op.drop_index("ix_topics_type_active", table_name="topics")
    op.drop_index("ix_topics_profile_active_flag", table_name="topics")
    op.drop_index("ix_topics_profile_id_active", table_name="topics")
    op.drop_table("topics")
    bind = op.get_bind()
    sa.Enum(name="topic_type_enum", native_enum=False).drop(bind, checkfirst=True)
