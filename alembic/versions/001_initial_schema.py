"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-27

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enums
    worker_status = sa.Enum("available", "assigned", "on_leave", name="worker_status_enum")
    skill_level = sa.Enum("junior", "experienced", "senior", name="skill_level_enum")
    round_status = sa.Enum("draft", "analyzing", "analyzed", "completed", name="round_status_enum")
    schedule_status = sa.Enum("scheduled", "in_progress", "completed", "cancelled", name="schedule_status_enum")
    notif_category = sa.Enum("weather", "labor", "quality", "schedule", "reminder", name="notification_category_enum")
    alert_sev = sa.Enum("info", "warning", "critical", name="alert_severity_enum")

    # 1. fields
    op.create_table(
        "fields",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("region", sa.String(100), nullable=False),
        sa.Column("area_hectares", sa.Numeric(6, 2), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False, server_default="6.927100"),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False, server_default="80.600500"),
        sa.Column("elevation_meters", sa.Numeric(7, 2), server_default="1200.00"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. workers
    op.create_table(
        "workers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("status", worker_status, nullable=False, server_default="available"),
        sa.Column("skill_level", skill_level, nullable=False, server_default="experienced"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone"),
    )

    # 3. harvest_rounds
    op.create_table(
        "harvest_rounds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("field_id", sa.Uuid(), nullable=False),
        sa.Column("round_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("field_area_hectares", sa.Numeric(6, 2)),
        sa.Column("predicted_yield_kg", sa.Numeric(8, 2)),
        sa.Column("actual_yield_kg", sa.Numeric(8, 2)),
        sa.Column("avg_pluckable_ratio", sa.Numeric(5, 4)),
        sa.Column("total_arimbu_count", sa.Integer(), server_default="0"),
        sa.Column("total_pluckable_count", sa.Integer(), server_default="0"),
        sa.Column("total_captured_area_sqm", sa.Numeric(8, 2), server_default="0"),
        sa.Column("labor_priority", sa.String(30)),
        sa.Column("readiness_status", sa.String(30), server_default="awaiting_analysis"),
        sa.Column("status", round_status, nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_harvest_rounds_field_id"), "harvest_rounds", ["field_id"], unique=False)

    # 4. analysis_images
    op.create_table(
        "analysis_images",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("harvest_round_id", sa.Uuid(), nullable=False),
        sa.Column("firebase_url", sa.Text(), nullable=False),
        sa.Column("firebase_path", sa.String(500), nullable=False),
        sa.Column("source_label", sa.String(50), nullable=False),
        sa.Column("arimbu_count", sa.Integer(), server_default="0"),
        sa.Column("pluckable_count", sa.Integer(), server_default="0"),
        sa.Column("captured_area_sqm", sa.Numeric(8, 2), server_default="0"),
        sa.Column("pluckable_ratio", sa.Numeric(5, 4)),
        sa.Column("is_analyzed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["harvest_round_id"], ["harvest_rounds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_images_harvest_round_id"), "analysis_images", ["harvest_round_id"], unique=False)
    op.create_index(op.f("ix_analysis_images_is_analyzed"), "analysis_images", ["is_analyzed"], unique=False)

    # 5. bud_markers
    op.create_table(
        "bud_markers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_image_id", sa.Uuid(), nullable=False),
        sa.Column("x_position", sa.Numeric(7, 4), nullable=False),
        sa.Column("y_position", sa.Numeric(7, 4), nullable=False),
        sa.Column("marker_type", sa.String(20), server_default="bud"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["analysis_image_id"], ["analysis_images.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bud_markers_analysis_image_id"), "bud_markers", ["analysis_image_id"], unique=False)

    # 6. worker_field_assignments
    op.create_table(
        "worker_field_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("worker_id", sa.Uuid(), nullable=False),
        sa.Column("field_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("unassigned_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("worker_id", "field_id", name="uq_worker_field_active"),
    )

    # 7. plucking_schedules
    op.create_table(
        "plucking_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("field_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("shift_start", sa.Time(), nullable=False),
        sa.Column("shift_end", sa.Time(), nullable=False),
        sa.Column("status", schedule_status, nullable=False, server_default="scheduled"),
        sa.Column("recommended_workers", sa.Integer(), server_default="5"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 8. schedule_workers
    op.create_table(
        "schedule_workers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schedule_id", sa.Uuid(), nullable=False),
        sa.Column("worker_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["schedule_id"], ["plucking_schedules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schedule_id", "worker_id", name="uq_schedule_worker"),
    )

    # 9. weather_logs
    op.create_table(
        "weather_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("harvest_round_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.String(100)),
        sa.Column("rain_chance_pct", sa.Integer()),
        sa.Column("humidity_pct", sa.Integer()),
        sa.Column("temperature_c", sa.Numeric(5, 2)),
        sa.Column("wind_speed_kmh", sa.Numeric(5, 2)),
        sa.Column("storm_risk", sa.Boolean(), server_default="false"),
        sa.Column("weather_code", sa.Integer()),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["harvest_round_id"], ["harvest_rounds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("harvest_round_id"),
    )

    # 10. notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("field_id", sa.Uuid()),
        sa.Column("harvest_round_id", sa.Uuid()),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("category", notif_category, nullable=False),
        sa.Column("severity", alert_sev, nullable=False, server_default="info"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["harvest_round_id"], ["harvest_rounds.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_field_id"), "notifications", ["field_id"], unique=False)

    workers_table = sa.table(
        "workers",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String),
        sa.column("phone", sa.String),
        sa.column("status", sa.String),
        sa.column("skill_level", sa.String),
    )
    op.bulk_insert(
        workers_table,
        [
            {"id": uuid.uuid4(), "name": "Saman Perera", "phone": "+94771234567", "status": "available", "skill_level": "senior"},
            {"id": uuid.uuid4(), "name": "Nimali Silva", "phone": "+94772345678", "status": "available", "skill_level": "experienced"},
            {"id": uuid.uuid4(), "name": "Kamal Bandara", "phone": "+94773456789", "status": "available", "skill_level": "junior"},
            {"id": uuid.uuid4(), "name": "Sunethra Devi", "phone": "+94774567890", "status": "available", "skill_level": "senior"},
        ],
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("weather_logs")
    op.drop_table("schedule_workers")
    op.drop_table("plucking_schedules")
    op.drop_table("worker_field_assignments")
    op.drop_table("bud_markers")
    op.drop_table("analysis_images")
    op.drop_table("harvest_rounds")
    op.drop_table("workers")
    op.drop_table("fields")

    sa.Enum(name="alert_severity_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="notification_category_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="schedule_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="round_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="skill_level_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="worker_status_enum").drop(op.get_bind(), checkfirst=True)
