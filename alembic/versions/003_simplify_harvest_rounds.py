"""Simplify harvest_rounds structure

Revision ID: 003
Revises: 002
Create Date: 2026-07-09

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("harvest_rounds")}

    if "pluckable_ratio" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column("pluckable_ratio", sa.Numeric(5, 4), nullable=True),
        )
    if "plucking_status" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column(
                "plucking_status",
                sa.String(length=30),
                nullable=False,
                server_default="awaiting_analysis",
            ),
        )
    if "predicted_yield" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column("predicted_yield", sa.Numeric(8, 2), nullable=True),
        )
    if "actual_yield" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column("actual_yield", sa.Numeric(8, 2), nullable=True),
        )
    if "is_completed" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column(
                "is_completed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    op.execute(
        """
        UPDATE harvest_rounds
        SET
            pluckable_ratio = avg_pluckable_ratio,
            plucking_status = COALESCE(readiness_status, 'awaiting_analysis'),
            predicted_yield = predicted_yield_kg,
            actual_yield = actual_yield_kg,
            is_completed = CASE WHEN status = 'completed' THEN true ELSE false END
        """
    )

    for column_name in (
        "round_date",
        "field_area_hectares",
        "predicted_yield_kg",
        "actual_yield_kg",
        "avg_pluckable_ratio",
        "total_arimbu_count",
        "total_pluckable_count",
        "total_captured_area_sqm",
        "labor_priority",
        "readiness_status",
        "status",
    ):
        if column_name in columns:
            op.drop_column("harvest_rounds", column_name)

    sa.Enum(name="round_status_enum").drop(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("harvest_rounds")}

    round_status_enum = sa.Enum(
        "draft",
        "analyzing",
        "analyzed",
        "completed",
        name="round_status_enum",
    )
    round_status_enum.create(bind, checkfirst=True)

    if "round_date" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column(
                "round_date",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
    if "field_area_hectares" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column("field_area_hectares", sa.Numeric(6, 2), nullable=True),
        )
    if "predicted_yield_kg" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column("predicted_yield_kg", sa.Numeric(8, 2), nullable=True),
        )
    if "actual_yield_kg" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column("actual_yield_kg", sa.Numeric(8, 2), nullable=True),
        )
    if "avg_pluckable_ratio" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column("avg_pluckable_ratio", sa.Numeric(5, 4), nullable=True),
        )
    if "total_arimbu_count" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column(
                "total_arimbu_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if "total_pluckable_count" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column(
                "total_pluckable_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if "total_captured_area_sqm" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column(
                "total_captured_area_sqm",
                sa.Numeric(8, 2),
                nullable=False,
                server_default="0",
            ),
        )
    if "labor_priority" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column("labor_priority", sa.String(length=30), nullable=True),
        )
    if "readiness_status" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column(
                "readiness_status",
                sa.String(length=30),
                nullable=False,
                server_default="awaiting_analysis",
            ),
        )
    if "status" not in columns:
        op.add_column(
            "harvest_rounds",
            sa.Column(
                "status",
                round_status_enum,
                nullable=False,
                server_default="draft",
            ),
        )

    op.execute(
        """
        UPDATE harvest_rounds
        SET
            predicted_yield_kg = predicted_yield,
            actual_yield_kg = actual_yield,
            avg_pluckable_ratio = pluckable_ratio,
            readiness_status = COALESCE(plucking_status, 'awaiting_analysis'),
            status = CASE WHEN is_completed THEN 'completed' ELSE 'draft' END
        """
    )

    for column_name in (
        "pluckable_ratio",
        "plucking_status",
        "predicted_yield",
        "actual_yield",
        "is_completed",
    ):
        if column_name in columns:
            op.drop_column("harvest_rounds", column_name)
