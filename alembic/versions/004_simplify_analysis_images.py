"""Simplify analysis_images structure

Revision ID: 004
Revises: 003
Create Date: 2026-07-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("analysis_images")}

    if "image_url" not in columns:
        op.add_column(
            "analysis_images",
            sa.Column("image_url", sa.Text(), nullable=True),
        )

    if "firebase_url" in columns:
        op.execute(
            """
            UPDATE analysis_images
            SET image_url = firebase_url
            WHERE image_url IS NULL
            """
        )

    op.alter_column("analysis_images", "image_url", nullable=False)

    if "ix_analysis_images_is_analyzed" in {
        idx["name"] for idx in inspector.get_indexes("analysis_images")
    }:
        op.drop_index("ix_analysis_images_is_analyzed", table_name="analysis_images")

    for column_name in (
        "firebase_url",
        "firebase_path",
        "source_label",
        "captured_area_sqm",
        "pluckable_ratio",
        "is_analyzed",
        "captured_at",
        "analyzed_at",
        "created_at",
    ):
        if column_name in columns:
            op.drop_column("analysis_images", column_name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("analysis_images")}

    if "firebase_url" not in columns:
        op.add_column(
            "analysis_images",
            sa.Column("firebase_url", sa.Text(), nullable=True),
        )
    if "firebase_path" not in columns:
        op.add_column(
            "analysis_images",
            sa.Column("firebase_path", sa.String(length=500), nullable=True),
        )
    if "source_label" not in columns:
        op.add_column(
            "analysis_images",
            sa.Column("source_label", sa.String(length=50), nullable=True),
        )
    if "captured_area_sqm" not in columns:
        op.add_column(
            "analysis_images",
            sa.Column("captured_area_sqm", sa.Numeric(8, 2), nullable=True),
        )
    if "pluckable_ratio" not in columns:
        op.add_column(
            "analysis_images",
            sa.Column("pluckable_ratio", sa.Numeric(5, 4), nullable=True),
        )
    if "is_analyzed" not in columns:
        op.add_column(
            "analysis_images",
            sa.Column("is_analyzed", sa.Boolean(), nullable=True),
        )
    if "captured_at" not in columns:
        op.add_column(
            "analysis_images",
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "analyzed_at" not in columns:
        op.add_column(
            "analysis_images",
            sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "created_at" not in columns:
        op.add_column(
            "analysis_images",
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "image_url" in columns:
        op.execute(
            """
            UPDATE analysis_images
            SET
                firebase_url = image_url,
                firebase_path = COALESCE(firebase_path, ''),
                source_label = COALESCE(source_label, 'Upload'),
                captured_area_sqm = COALESCE(captured_area_sqm, 0),
                pluckable_ratio = CASE
                    WHEN (arimbu_count + pluckable_count) > 0
                    THEN pluckable_count::numeric / (arimbu_count + pluckable_count)
                    ELSE 0
                END,
                is_analyzed = true,
                captured_at = COALESCE(captured_at, now()),
                created_at = COALESCE(created_at, now())
            """
        )
        op.alter_column("analysis_images", "firebase_url", nullable=False)
        op.alter_column("analysis_images", "firebase_path", nullable=False)
        op.alter_column("analysis_images", "source_label", nullable=False)
        op.alter_column("analysis_images", "captured_area_sqm", nullable=False)
        op.alter_column("analysis_images", "is_analyzed", nullable=False)
        op.alter_column("analysis_images", "captured_at", nullable=False)
        op.drop_column("analysis_images", "image_url")

    op.create_index(
        "ix_analysis_images_is_analyzed",
        "analysis_images",
        ["is_analyzed"],
        unique=False,
    )
