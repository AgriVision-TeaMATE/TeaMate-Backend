"""merge migration heads

Revision ID: b1dfe4b3a274
Revises: 010, 010_expand_field_area_precision
Create Date: 2026-07-30 02:12:05.841438

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1dfe4b3a274'
down_revision: Union[str, None] = ('010', '010_expand_field_area_precision')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
