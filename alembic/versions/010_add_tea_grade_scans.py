"""Add tea_grade_scans table

Revision ID: 010
Revises: 009
Create Date: 2026-07-25

"""
from alembic import op
import sqlalchemy as sa
revision = "010"
down_revision = "009_add_diseases_and_risk_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tea_grade_scans",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("scan_id", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("field_id", sa.Uuid(as_uuid=True), sa.ForeignKey("fields.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("image_url", sa.String, nullable=False),
        sa.Column("scan_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("grade_composition", sa.JSON, nullable=False),
        sa.Column("dominant_grade", sa.String(50), nullable=False),
        sa.Column("dominant_grade_percentage", sa.Float, nullable=False),
        sa.Column("total_particles_detected", sa.Integer, nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("inference_time_ms", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("tea_grade_scans")
