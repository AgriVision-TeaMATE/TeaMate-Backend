"""Expand field area precision for small plots

Revision ID: 010_expand_field_area_precision
Revises: 009_add_diseases_and_risk_columns
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "010_expand_field_area_precision"
down_revision = "009_add_diseases_and_risk_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "fields",
        "area_hectares",
        existing_type=sa.Numeric(6, 2),
        type_=sa.Numeric(10, 4),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "fields",
        "area_hectares",
        existing_type=sa.Numeric(10, 4),
        type_=sa.Numeric(6, 2),
        existing_nullable=False,
    )
