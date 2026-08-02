"""add disease explainability fields

Revision ID: d1c8e7e9a45d
Revises: b1dfe4b3a274
Create Date: 2026-07-30 02:13:55.738476

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1c8e7e9a45d"
down_revision: Union[str, None] = "b1dfe4b3a274"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.add_column(
        "disease_scans",
        sa.Column(
            "explanation_data",
            sa.JSON(),
            nullable=True
        )
    )

    op.add_column(
        "disease_scans",
        sa.Column(
            "environmental_summary",
            sa.String(length=1000),
            nullable=True
        )
    )

    op.add_column(
        "disease_scans",
        sa.Column(
            "environmental_insights",
            sa.JSON(),
            nullable=True
        )
    )

    op.add_column(
        "disease_scans",
        sa.Column(
            "environmental_technical_summary",
            sa.JSON(),
            nullable=True
        )
    )


def downgrade() -> None:

    op.drop_column(
        "disease_scans",
        "environmental_technical_summary"
    )

    op.drop_column(
        "disease_scans",
        "environmental_insights"
    )

    op.drop_column(
        "disease_scans",
        "environmental_summary"
    )

    op.drop_column(
        "disease_scans",
        "explanation_data"
    )