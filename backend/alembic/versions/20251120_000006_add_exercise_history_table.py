"""Add exercise history table for exercises tracking."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20251120_000006"
down_revision = "20251119_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    exercise_type_enum = sa.Enum(
        "free_text",
        "multiple_choice",
        name="exercise_type_enum",
        native_enum=False,
    )
    exercise_result_enum = sa.Enum(
        "correct",
        "partial",
        "incorrect",
        name="exercise_result_enum",
        native_enum=False,
    )
    bind = op.get_bind()
    exercise_type_enum.create(bind, checkfirst=True)
    exercise_result_enum.create(bind, checkfirst=True)

    op.create_table(
        "exercise_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", exercise_type_enum, nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("user_answer", sa.Text(), nullable=False),
        sa.Column("result", exercise_result_enum, nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "used_hint",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "completed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["language_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_index("ix_exercise_history_user_id", "exercise_history", ["user_id"])
    op.create_index("ix_exercise_history_topic_id", "exercise_history", ["topic_id"])
    op.create_index("ix_exercise_history_profile_id", "exercise_history", ["profile_id"])
    op.create_index("ix_exercise_history_result", "exercise_history", ["result"])
    op.create_index(
        "ix_exercise_history_completed_at",
        "exercise_history",
        ["completed_at"],
    )
    op.create_index(
        "ix_exercise_history_user_profile",
        "exercise_history",
        ["user_id", "profile_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_exercise_history_user_profile", table_name="exercise_history")
    op.drop_index("ix_exercise_history_completed_at", table_name="exercise_history")
    op.drop_index("ix_exercise_history_result", table_name="exercise_history")
    op.drop_index("ix_exercise_history_profile_id", table_name="exercise_history")
    op.drop_index("ix_exercise_history_topic_id", table_name="exercise_history")
    op.drop_index("ix_exercise_history_user_id", table_name="exercise_history")
    op.drop_table("exercise_history")

    bind = op.get_bind()
    sa.Enum(name="exercise_result_enum", native_enum=False).drop(bind, checkfirst=True)
    sa.Enum(name="exercise_type_enum", native_enum=False).drop(bind, checkfirst=True)
