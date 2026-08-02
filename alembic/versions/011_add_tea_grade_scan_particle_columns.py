"""Add particle/segmentation columns to tea_grade_scans

Revision ID: 011
Revises: 010
Create Date: 2026-08-02

"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tea_grade_scans", sa.Column("num_particles_classified", sa.Integer, nullable=True))
    op.add_column("tea_grade_scans", sa.Column("particles", sa.JSON, nullable=True))
    op.add_column("tea_grade_scans", sa.Column("segmented_image_base64", sa.String, nullable=True))
    op.add_column("tea_grade_scans", sa.Column("method", sa.String(50), nullable=True))
    op.add_column("tea_grade_scans", sa.Column("weighting", sa.String(20), nullable=True))
    op.add_column("tea_grade_scans", sa.Column("px_per_mm_used", sa.Float, nullable=True))


def downgrade() -> None:
    op.drop_column("tea_grade_scans", "px_per_mm_used")
    op.drop_column("tea_grade_scans", "weighting")
    op.drop_column("tea_grade_scans", "method")
    op.drop_column("tea_grade_scans", "segmented_image_base64")
    op.drop_column("tea_grade_scans", "particles")
    op.drop_column("tea_grade_scans", "num_particles_classified")
