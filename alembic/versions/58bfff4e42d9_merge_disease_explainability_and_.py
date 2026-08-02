"""merge disease explainability and particle segmentation heads

Revision ID: 58bfff4e42d9
Revises: 011, d1c8e7e9a45d
Create Date: 2026-08-02 21:26:08.215437

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58bfff4e42d9'
down_revision: Union[str, None] = ('011', 'd1c8e7e9a45d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
