"""align disease_scans columns with model (image_urls, explanation fields)

Revision ID: f754e6669b12
Revises: faf66393cf7e
Create Date: 2026-08-02 21:56:06.189869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f754e6669b12'
down_revision: Union[str, None] = 'faf66393cf7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("disease_scans", "image_url")
    op.add_column("disease_scans", sa.Column("image_urls", sa.JSON(), nullable=False, server_default="[]"))
    op.alter_column("disease_scans", "image_urls", server_default=None)

    op.add_column("disease_scans", sa.Column("explanation_data", sa.JSON(), nullable=True))
    op.add_column("disease_scans", sa.Column("environmental_summary", sa.String(1000), nullable=True))
    op.add_column("disease_scans", sa.Column("environmental_insights", sa.JSON(), nullable=True))
    op.add_column("disease_scans", sa.Column("environmental_technical_summary", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("disease_scans", "environmental_technical_summary")
    op.drop_column("disease_scans", "environmental_insights")
    op.drop_column("disease_scans", "environmental_summary")
    op.drop_column("disease_scans", "explanation_data")

    op.drop_column("disease_scans", "image_urls")
    op.add_column("disease_scans", sa.Column("image_url", sa.String(), nullable=False))
