"""BT2 shadow pick eval performance fields.

Revision ID: r7s8t9u0v1w2
Revises: q1r2s3t4u5v6
"""

from alembic import op
import sqlalchemy as sa

revision = "r7s8t9u0v1w2"
down_revision = "q1r2s3t4u5v6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bt2_shadow_pick_eval", sa.Column("evaluation_reason", sa.Text(), nullable=True))
    op.add_column("bt2_shadow_pick_eval", sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bt2_shadow_pick_eval", sa.Column("truth_source", sa.String(length=64), nullable=True))
    op.add_column("bt2_shadow_pick_eval", sa.Column("result_home", sa.Integer(), nullable=True))
    op.add_column("bt2_shadow_pick_eval", sa.Column("result_away", sa.Integer(), nullable=True))
    op.add_column("bt2_shadow_pick_eval", sa.Column("event_status", sa.String(length=32), nullable=True))
    op.add_column("bt2_shadow_pick_eval", sa.Column("decimal_odds", sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column(
        "bt2_shadow_pick_eval",
        sa.Column("roi_flat_stake_units", sa.Numeric(precision=10, scale=4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bt2_shadow_pick_eval", "roi_flat_stake_units")
    op.drop_column("bt2_shadow_pick_eval", "decimal_odds")
    op.drop_column("bt2_shadow_pick_eval", "event_status")
    op.drop_column("bt2_shadow_pick_eval", "result_away")
    op.drop_column("bt2_shadow_pick_eval", "result_home")
    op.drop_column("bt2_shadow_pick_eval", "truth_source")
    op.drop_column("bt2_shadow_pick_eval", "evaluated_at")
    op.drop_column("bt2_shadow_pick_eval", "evaluation_reason")
