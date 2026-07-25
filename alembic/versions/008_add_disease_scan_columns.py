"""Add missing columns to disease_scans table

Revision ID: 008
Revises: 007
Create Date: 2026-07-22

"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create base table (never captured by an earlier migration)
    op.create_table(
        "disease_scans",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("field_id", sa.Uuid(as_uuid=True), sa.ForeignKey("fields.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("image_url", sa.String, nullable=False),
        sa.Column("detected_disease", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("treatment_suggestions", sa.JSON, nullable=True),
        sa.Column("environmental_data", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Add missing columns
    op.add_column("disease_scans", sa.Column("scan_id", sa.String(64), unique=True, index=True, nullable=False))
    op.add_column("disease_scans", sa.Column("description", sa.String(500), nullable=True))
    op.add_column("disease_scans", sa.Column("latitude", sa.Float, nullable=True))
    op.add_column("disease_scans", sa.Column("longitude", sa.Float, nullable=True))
    op.add_column("disease_scans", sa.Column("scan_datetime", sa.DateTime(timezone=True), nullable=False))
    op.add_column("disease_scans", sa.Column("weather_summary", sa.JSON, nullable=True))
    op.add_column("disease_scans", sa.Column("all_predictions", sa.JSON, nullable=True))
    op.add_column("disease_scans", sa.Column("ai_explanation", sa.String, nullable=True))
    op.add_column("disease_scans", sa.Column("model_version", sa.String(50), nullable=True))
    op.add_column("disease_scans", sa.Column("inference_time_ms", sa.Float, nullable=True))

    # Backfill scan_datetime with created_at values for existing rows
    op.execute("""
        UPDATE disease_scans
        SET scan_datetime = created_at
        WHERE scan_datetime IS NULL
    """)


def downgrade() -> None:
    op.drop_column("disease_scans", "inference_time_ms")
    op.drop_column("disease_scans", "model_version")
    op.drop_column("disease_scans", "ai_explanation")
    op.drop_column("disease_scans", "all_predictions")
    op.drop_column("disease_scans", "weather_summary")
    op.drop_column("disease_scans", "scan_datetime")
    op.drop_column("disease_scans", "longitude")
    op.drop_column("disease_scans", "latitude")
    op.drop_column("disease_scans", "description")
    op.drop_column("disease_scans", "scan_id")
    op.drop_table("disease_scans")