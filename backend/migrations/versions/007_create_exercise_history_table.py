"""Create exercise_history table.

Revision ID: 007_create_exercise_history_table
Revises: 006_create_conversation_history_table
Create Date: 2024-11-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql


revision = "007_create_exercise_history_table"
down_revision = "006_create_conversation_history_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exercise_history",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", psql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_id", psql.UUID(as_uuid=True), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", psql.UUID(as_uuid=True), sa.ForeignKey("language_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("user_answer", sa.Text(), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("explanation", sa.Text()),
        sa.Column("used_hint", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("completed_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("type IN ('free_text','multiple_choice')", name="ck_exercise_history_type"),
        sa.CheckConstraint(
            "result IN ('correct','partial','incorrect')",
            name="ck_exercise_history_result",
        ),
    )

    op.create_index("idx_exercise_history_user_id", "exercise_history", ["user_id"])
    op.create_index("idx_exercise_history_topic_id", "exercise_history", ["topic_id"])
    op.create_index("idx_exercise_history_profile_id", "exercise_history", ["profile_id"])
    op.create_index("idx_exercise_history_completed_at", "exercise_history", ["completed_at"])
    op.create_index("idx_exercise_history_result", "exercise_history", ["result"])


def downgrade() -> None:
    op.drop_index("idx_exercise_history_result", table_name="exercise_history")
    op.drop_index("idx_exercise_history_completed_at", table_name="exercise_history")
    op.drop_index("idx_exercise_history_profile_id", table_name="exercise_history")
    op.drop_index("idx_exercise_history_topic_id", table_name="exercise_history")
    op.drop_index("idx_exercise_history_user_id", table_name="exercise_history")
    op.drop_table("exercise_history")
