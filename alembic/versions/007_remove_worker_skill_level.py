"""Remove worker skill level

Revision ID: 007
Revises: 006
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("workers")}
    if "skill_level" in columns:
        op.drop_column("workers", "skill_level")
    sa.Enum(name="skill_level_enum").drop(bind, checkfirst=True)


def downgrade() -> None:
    skill_level = sa.Enum(
        "junior",
        "experienced",
        "senior",
        name="skill_level_enum",
    )
    skill_level.create(op.get_bind(), checkfirst=True)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("workers")}
    if "skill_level" not in columns:
        op.add_column(
            "workers",
            sa.Column(
                "skill_level",
                skill_level,
                nullable=False,
                server_default="experienced",
            ),
        )
