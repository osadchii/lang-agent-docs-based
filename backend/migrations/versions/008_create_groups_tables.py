"""Create groups and related tables.

Revision ID: 008_create_groups_tables
Revises: 007_create_exercise_history_table
Create Date: 2024-11-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql


revision = "008_create_groups_tables"
down_revision = "007_create_exercise_history_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_id", psql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("max_members", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("members_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index(
        "idx_groups_owner_id",
        "groups",
        ["owner_id"],
        postgresql_where=sa.text("deleted = FALSE"),
    )

    op.execute(
        """
        CREATE TRIGGER update_groups_updated_at
        BEFORE UPDATE ON groups
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    )

    op.create_table(
        "group_members",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("group_id", psql.UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", psql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default=sa.text("'member'")),
        sa.Column("joined_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("role IN ('member')", name="ck_group_members_role"),
    )

    op.create_index("idx_group_members_group_id", "group_members", ["group_id"])
    op.create_index("idx_group_members_user_id", "group_members", ["user_id"])
    op.execute(
        """
        CREATE UNIQUE INDEX idx_group_members_unique
        ON group_members (group_id, user_id);
        """
    )

    op.create_table(
        "group_materials",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("group_id", psql.UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_type", sa.String(length=20), nullable=False),
        sa.Column("shared_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("material_type IN ('deck','topic')", name="ck_group_materials_type"),
    )

    op.create_index("idx_group_materials_group_id", "group_materials", ["group_id"])
    op.create_index(
        "idx_group_materials_material_id_type",
        "group_materials",
        ["material_id", "material_type"],
    )
    op.execute(
        """
        CREATE UNIQUE INDEX idx_group_materials_unique
        ON group_materials (group_id, material_id, material_type);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_group_materials_unique")
    op.drop_index("idx_group_materials_material_id_type", table_name="group_materials")
    op.drop_index("idx_group_materials_group_id", table_name="group_materials")
    op.drop_table("group_materials")

    op.execute("DROP INDEX IF EXISTS idx_group_members_unique")
    op.drop_index("idx_group_members_user_id", table_name="group_members")
    op.drop_index("idx_group_members_group_id", table_name="group_members")
    op.drop_table("group_members")

    op.execute("DROP TRIGGER IF EXISTS update_groups_updated_at ON groups")
    op.drop_index("idx_groups_owner_id", table_name="groups")
    op.drop_table("groups")
