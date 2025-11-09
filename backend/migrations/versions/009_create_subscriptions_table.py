"""Create subscriptions table.

Revision ID: 009_create_subscriptions_table
Revises: 008_create_groups_tables
Create Date: 2024-11-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql


revision = "009_create_subscriptions_table"
down_revision = "008_create_groups_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", psql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255)),
        sa.Column("stripe_subscription_id", sa.String(length=255)),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("plan", sa.String(length=20)),
        sa.Column("price", sa.Numeric(10, 2)),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'EUR'")),
        sa.Column("current_period_start", sa.DateTime()),
        sa.Column("current_period_end", sa.DateTime()),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("canceled_at", sa.DateTime()),
        sa.Column("payment_method_type", sa.String(length=50)),
        sa.Column("payment_method_last4", sa.String(length=4)),
        sa.Column("payment_method_brand", sa.String(length=50)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("status IN ('free','trial','active','canceled','expired')", name="ck_subscriptions_status"),
        sa.CheckConstraint("plan IS NULL OR plan IN ('monthly','yearly')", name="ck_subscriptions_plan"),
    )

    op.create_index("idx_subscriptions_user_id", "subscriptions", ["user_id"], unique=True)
    op.create_index(
        "idx_subscriptions_stripe_customer",
        "subscriptions",
        ["stripe_customer_id"],
        unique=True,
    )
    op.create_index(
        "idx_subscriptions_stripe_subscription",
        "subscriptions",
        ["stripe_subscription_id"],
        unique=True,
    )
    op.create_index("idx_subscriptions_status", "subscriptions", ["status"])
    op.create_index("idx_subscriptions_period_end", "subscriptions", ["current_period_end"])

    op.execute(
        """
        CREATE TRIGGER update_subscriptions_updated_at
        BEFORE UPDATE ON subscriptions
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_subscriptions_updated_at ON subscriptions")
    op.drop_index("idx_subscriptions_period_end", table_name="subscriptions")
    op.drop_index("idx_subscriptions_status", table_name="subscriptions")
    op.drop_index("idx_subscriptions_stripe_subscription", table_name="subscriptions")
    op.drop_index("idx_subscriptions_stripe_customer", table_name="subscriptions")
    op.drop_index("idx_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")
