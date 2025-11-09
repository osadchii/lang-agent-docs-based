"""Create updated_at trigger helper.

Revision ID: 000_update_updated_at_function
Revises: 
Create Date: 2024-11-09
"""

from alembic import op


revision = "000_update_updated_at_function"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
