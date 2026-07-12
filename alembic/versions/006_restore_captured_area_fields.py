"""Restore captured area fields for analysis images and harvest rounds

Revision ID: 006
Revises: 005
Create Date: 2026-07-12

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    image_columns = {col["name"] for col in inspector.get_columns("analysis_images")}
    if "captured_area_sqm" not in image_columns:
        op.add_column(
            "analysis_images",
            sa.Column(
                "captured_area_sqm",
                sa.Numeric(8, 2),
                nullable=False,
                server_default="0",
            ),
        )

    round_columns = {col["name"] for col in inspector.get_columns("harvest_rounds")}
    if "total_captured_area_sqm" not in round_columns:
        op.add_column(
            "harvest_rounds",
            sa.Column(
                "total_captured_area_sqm",
                sa.Numeric(8, 2),
                nullable=False,
                server_default="0",
            ),
        )

    op.execute(
        """
        UPDATE harvest_rounds
        SET total_captured_area_sqm = COALESCE((
            SELECT SUM(COALESCE(ai.captured_area_sqm, 0))
            FROM analysis_images ai
            WHERE ai.harvest_round_id = harvest_rounds.id
        ), 0)
        """
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    round_columns = {col["name"] for col in inspector.get_columns("harvest_rounds")}
    if "total_captured_area_sqm" in round_columns:
        op.drop_column("harvest_rounds", "total_captured_area_sqm")

    image_columns = {col["name"] for col in inspector.get_columns("analysis_images")}
    if "captured_area_sqm" in image_columns:
        op.drop_column("analysis_images", "captured_area_sqm")
