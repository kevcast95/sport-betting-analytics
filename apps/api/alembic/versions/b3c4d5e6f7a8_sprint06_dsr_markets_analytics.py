"""Sprint 06 — DSR metadata en daily_picks, mercado canónico y analytics en picks.

US-BE-025, US-BE-027, US-BE-028 — D-06-002, D-06-003, D-06-015.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bt2_daily_picks",
        sa.Column("pipeline_version", sa.String(length=40), nullable=False, server_default="s6-rules-v0"),
    )
    op.add_column("bt2_daily_picks", sa.Column("dsr_input_hash", sa.String(length=64), nullable=True))
    op.add_column("bt2_daily_picks", sa.Column("dsr_narrative_es", sa.Text(), nullable=True))
    op.add_column(
        "bt2_daily_picks",
        sa.Column("dsr_confidence_label", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "bt2_daily_picks",
        sa.Column("model_market_canonical", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "bt2_daily_picks",
        sa.Column("model_selection_canonical", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "bt2_daily_picks",
        sa.Column("dsr_source", sa.String(length=24), nullable=False, server_default="rules_fallback"),
    )
    op.alter_column("bt2_daily_picks", "pipeline_version", server_default=None)
    op.alter_column("bt2_daily_picks", "dsr_source", server_default=None)

    op.add_column(
        "bt2_picks",
        sa.Column("market_canonical", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "bt2_picks",
        sa.Column("model_market_canonical", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "bt2_picks",
        sa.Column("model_selection_canonical", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "bt2_picks",
        sa.Column(
            "model_prediction_result",
            sa.String(length=8),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE bt2_picks
        SET market_canonical = CASE
            WHEN market ILIKE '%%1X2%%' OR market ILIKE '%%WINNER%%' OR market ILIKE '%%MATCH%%' THEN 'FT_1X2'
            WHEN market ILIKE '%%TOTAL%%' OR market ILIKE '%%GOALS%%' OR market ILIKE '%%OVER%%'
                 OR market ILIKE '%%UNDER%%' THEN 'OU_GOALS_2_5'
            ELSE 'UNKNOWN'
        END
        WHERE market_canonical IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("bt2_picks", "model_prediction_result")
    op.drop_column("bt2_picks", "model_selection_canonical")
    op.drop_column("bt2_picks", "model_market_canonical")
    op.drop_column("bt2_picks", "market_canonical")

    op.drop_column("bt2_daily_picks", "dsr_source")
    op.drop_column("bt2_daily_picks", "model_selection_canonical")
    op.drop_column("bt2_daily_picks", "model_market_canonical")
    op.drop_column("bt2_daily_picks", "dsr_confidence_label")
    op.drop_column("bt2_daily_picks", "dsr_narrative_es")
    op.drop_column("bt2_daily_picks", "dsr_input_hash")
    op.drop_column("bt2_daily_picks", "pipeline_version")
