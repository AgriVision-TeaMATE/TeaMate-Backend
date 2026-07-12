"""Link plucking schedules to harvest rounds

Revision ID: 005
Revises: 004
Create Date: 2026-07-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {col["name"] for col in inspector.get_columns("plucking_schedules")}
    if "harvest_round_id" not in columns:
        op.add_column(
            "plucking_schedules",
            sa.Column("harvest_round_id", sa.Uuid(), nullable=True),
        )
        op.create_foreign_key(
            "fk_plucking_schedules_harvest_round_id",
            "plucking_schedules",
            "harvest_rounds",
            ["harvest_round_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {col["name"] for col in inspector.get_columns("plucking_schedules")}
    if "harvest_round_id" in columns:
        op.drop_constraint(
            "fk_plucking_schedules_harvest_round_id",
            "plucking_schedules",
            type_="foreignkey",
        )
        op.drop_column("plucking_schedules", "harvest_round_id")
