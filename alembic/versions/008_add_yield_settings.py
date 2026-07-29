"""Add yield settings

Revision ID: 008
Revises: 007
Create Date: 2026-07-26
"""

from alembic import op
import sqlalchemy as sa


revision = "008_yield_settings"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "yield_settings" in tables:
        return

    op.create_table(
        "yield_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tea_variant", sa.String(length=100), nullable=False, server_default="TRI 2025"),
        sa.Column("pluckable_100_bud_weight_g", sa.Numeric(8, 2), nullable=True),
        sa.Column("arimbu_100_bud_weight_g", sa.Numeric(8, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        op.f("ix_yield_settings_user_id"),
        "yield_settings",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "yield_settings" not in tables:
        return

    op.drop_index(op.f("ix_yield_settings_user_id"), table_name="yield_settings")
    op.drop_table("yield_settings")
