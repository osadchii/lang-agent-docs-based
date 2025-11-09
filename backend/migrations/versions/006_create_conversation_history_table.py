"""Create conversation_history table.

Revision ID: 006_create_conversation_history_table
Revises: 005_create_topics_table
Create Date: 2024-11-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql


revision = "006_create_conversation_history_table"
down_revision = "005_create_topics_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_history",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", psql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", psql.UUID(as_uuid=True), sa.ForeignKey("language_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("role IN ('user','assistant','system')", name="ck_conversation_history_role"),
    )

    op.create_index(
        "idx_conversation_user_profile",
        "conversation_history",
        ["user_id", "profile_id"],
    )
    op.create_index(
        "idx_conversation_timestamp",
        "conversation_history",
        ["timestamp"],
    )


def downgrade() -> None:
    op.drop_index("idx_conversation_timestamp", table_name="conversation_history")
    op.drop_index("idx_conversation_user_profile", table_name="conversation_history")
    op.drop_table("conversation_history")
