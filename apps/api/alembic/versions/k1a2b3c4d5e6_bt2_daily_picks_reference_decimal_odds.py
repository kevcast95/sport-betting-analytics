"""bt2_daily_picks: cuota consenso al momento de generar el pick (ROI / monitor).

Revision ID: k1a2b3c4d5e6
Revises: j4k5l6m7n8o9
"""

from alembic import op
import sqlalchemy as sa

revision = "k1a2b3c4d5e6"
down_revision = "j4k5l6m7n8o9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bt2_daily_picks",
        sa.Column("reference_decimal_odds", sa.Numeric(10, 4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bt2_daily_picks", "reference_decimal_odds")
