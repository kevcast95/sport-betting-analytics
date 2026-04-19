"""Señal pick: 4 dimensiones (prob, evidence, predictive, product action) + coherencia vía columnas.

Reemplaza el uso monolítico de dsr_confidence_label en producto; se mantiene la columna legada.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "l2m3n4o5p6"
down_revision = "m8n7o6p5q4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bt2_daily_picks",
        sa.Column("estimated_hit_probability", sa.Numeric(10, 8), nullable=True),
    )
    op.add_column(
        "bt2_daily_picks",
        sa.Column("evidence_quality", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "bt2_daily_picks",
        sa.Column("predictive_tier", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "bt2_daily_picks",
        sa.Column("action_tier", sa.String(length=12), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bt2_daily_picks", "action_tier")
    op.drop_column("bt2_daily_picks", "predictive_tier")
    op.drop_column("bt2_daily_picks", "evidence_quality")
    op.drop_column("bt2_daily_picks", "estimated_hit_probability")
