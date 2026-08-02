"""add missing category column to diseases

Revision ID: faf66393cf7e
Revises: 58bfff4e42d9
Create Date: 2026-08-02 21:51:40.803726

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'faf66393cf7e'
down_revision: Union[str, None] = '58bfff4e42d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "diseases",
        sa.Column("category", sa.String(50), nullable=False, server_default="unknown"),
    )


def downgrade() -> None:
    op.drop_column("diseases", "category")
