"""Reshape fields table for user ownership

Revision ID: 002
Revises: 001
Create Date: 2026-07-09

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("full_name", sa.String(length=150), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column(
                "role",
                sa.String(length=50),
                nullable=False,
                server_default="estate_manager",
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
        )
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.execute("DELETE FROM notifications")
    op.execute("DELETE FROM weather_logs")
    op.execute("DELETE FROM schedule_workers")
    op.execute("DELETE FROM plucking_schedules")
    op.execute("DELETE FROM worker_field_assignments")
    op.execute("DELETE FROM bud_markers")
    op.execute("DELETE FROM analysis_images")
    op.execute("DELETE FROM harvest_rounds")
    op.execute("DELETE FROM fields")

    field_columns = {col["name"] for col in inspector.get_columns("fields")}

    if "user_id" not in field_columns:
        op.add_column("fields", sa.Column("user_id", sa.Uuid(), nullable=True))
        op.create_index(op.f("ix_fields_user_id"), "fields", ["user_id"], unique=False)
        op.create_foreign_key(
            "fk_fields_user_id_users",
            "fields",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.alter_column("fields", "user_id", nullable=False)

    for column_name in ("region", "latitude", "longitude", "elevation_meters"):
        if column_name in field_columns:
            op.drop_column("fields", column_name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    field_columns = {col["name"] for col in inspector.get_columns("fields")}

    if "region" not in field_columns:
        op.add_column(
            "fields",
            sa.Column("region", sa.String(length=100), nullable=False, server_default=""),
        )
    if "latitude" not in field_columns:
        op.add_column(
            "fields",
            sa.Column(
                "latitude",
                sa.Numeric(precision=9, scale=6),
                nullable=False,
                server_default="6.927100",
            ),
        )
    if "longitude" not in field_columns:
        op.add_column(
            "fields",
            sa.Column(
                "longitude",
                sa.Numeric(precision=9, scale=6),
                nullable=False,
                server_default="80.600500",
            ),
        )
    if "elevation_meters" not in field_columns:
        op.add_column(
            "fields",
            sa.Column(
                "elevation_meters",
                sa.Numeric(precision=7, scale=2),
                nullable=True,
                server_default="1200.00",
            ),
        )

    if "user_id" in field_columns:
        op.drop_constraint("fk_fields_user_id_users", "fields", type_="foreignkey")
        op.drop_index(op.f("ix_fields_user_id"), table_name="fields")
        op.drop_column("fields", "user_id")
