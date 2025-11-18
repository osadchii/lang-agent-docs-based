"""Add group entities for shared study materials."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20251118_000004"
down_revision = "20251115_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    group_invite_status_enum = sa.Enum(
        "pending",
        "accepted",
        "declined",
        "expired",
        name="group_invite_status_enum",
        native_enum=False,
    )
    group_material_type_enum = sa.Enum(
        "deck",
        "topic",
        name="group_material_type_enum",
        native_enum=False,
    )
    bind = op.get_bind()
    group_invite_status_enum.create(bind, checkfirst=True)
    group_material_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("max_members", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("members_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
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
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("members_count >= 0", name="ck_groups_members_count_positive"),
        sa.CheckConstraint("max_members > 0", name="ck_groups_max_members_positive"),
    )
    op.create_index(
        "ix_groups_owner_id_active",
        "groups",
        ["owner_id"],
        postgresql_where=sa.text("deleted = FALSE"),
    )

    op.create_table(
        "group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default=sa.text("'member'")),
        sa.Column(
            "joined_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("group_id", "user_id", name="ux_group_members_group_user"),
    )
    op.create_index("ix_group_members_group_id", "group_members", ["group_id"])
    op.create_index("ix_group_members_user_id", "group_members", ["user_id"])

    op.create_table(
        "group_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inviter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invitee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            group_invite_status_enum,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("responded_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inviter_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invitee_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_group_invites_group_id", "group_invites", ["group_id"])
    op.create_index("ix_group_invites_invitee_id", "group_invites", ["invitee_id"])
    op.create_index("ix_group_invites_status", "group_invites", ["status"])
    op.create_index(
        "ix_group_invites_pending_unique",
        "group_invites",
        ["group_id", "invitee_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )

    op.create_table(
        "group_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_type", group_material_type_enum, nullable=False),
        sa.Column(
            "shared_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "group_id",
            "material_id",
            "material_type",
            name="ux_group_materials_unique",
        ),
    )
    op.create_index("ix_group_materials_group_id", "group_materials", ["group_id"])
    op.create_index(
        "ix_group_materials_material_type",
        "group_materials",
        ["material_id", "material_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_group_materials_material_type",
        table_name="group_materials",
    )
    op.drop_index("ix_group_materials_group_id", table_name="group_materials")
    op.drop_table("group_materials")

    op.drop_index("ix_group_invites_pending_unique", table_name="group_invites")
    op.drop_index("ix_group_invites_status", table_name="group_invites")
    op.drop_index("ix_group_invites_invitee_id", table_name="group_invites")
    op.drop_index("ix_group_invites_group_id", table_name="group_invites")
    op.drop_table("group_invites")

    op.drop_index("ix_group_members_user_id", table_name="group_members")
    op.drop_index("ix_group_members_group_id", table_name="group_members")
    op.drop_table("group_members")

    op.drop_index("ix_groups_owner_id_active", table_name="groups")
    op.drop_table("groups")

    bind = op.get_bind()
    sa.Enum(name="group_material_type_enum").drop(bind, checkfirst=True)
    sa.Enum(name="group_invite_status_enum").drop(bind, checkfirst=True)
