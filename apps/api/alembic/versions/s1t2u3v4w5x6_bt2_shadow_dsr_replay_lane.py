"""BT2 shadow — carril DSR replay (no pisa baseline no-DSR).

Revision ID: s1t2u3v4w5x6
Revises: r7s8t9u0v1w2
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "s1t2u3v4w5x6"
down_revision = "r7s8t9u0v1w2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bt2_shadow_runs",
        sa.Column("run_family", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "bt2_shadow_runs",
        sa.Column("selection_source", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_bt2_shadow_runs_run_family",
        "bt2_shadow_runs",
        ["run_family"],
        unique=False,
    )
    op.create_index(
        "ix_bt2_shadow_runs_selection_source",
        "bt2_shadow_runs",
        ["selection_source"],
        unique=False,
    )

    op.add_column(
        "bt2_shadow_daily_picks",
        sa.Column("dsr_parse_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "bt2_shadow_daily_picks",
        sa.Column("dsr_failure_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "bt2_shadow_daily_picks",
        sa.Column("dsr_model", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "bt2_shadow_daily_picks",
        sa.Column("dsr_prompt_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "bt2_shadow_daily_picks",
        sa.Column("dsr_response_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "bt2_shadow_daily_picks",
        sa.Column("dsr_usage_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "bt2_shadow_daily_picks",
        sa.Column("dsr_raw_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "bt2_shadow_daily_picks",
        sa.Column("selected_side_canonical", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bt2_shadow_daily_picks", "selected_side_canonical")
    op.drop_column("bt2_shadow_daily_picks", "dsr_raw_summary_json")
    op.drop_column("bt2_shadow_daily_picks", "dsr_usage_json")
    op.drop_column("bt2_shadow_daily_picks", "dsr_response_id")
    op.drop_column("bt2_shadow_daily_picks", "dsr_prompt_version")
    op.drop_column("bt2_shadow_daily_picks", "dsr_model")
    op.drop_column("bt2_shadow_daily_picks", "dsr_failure_reason")
    op.drop_column("bt2_shadow_daily_picks", "dsr_parse_status")

    op.drop_index("ix_bt2_shadow_runs_selection_source", table_name="bt2_shadow_runs")
    op.drop_index("ix_bt2_shadow_runs_run_family", table_name="bt2_shadow_runs")
    op.drop_column("bt2_shadow_runs", "selection_source")
    op.drop_column("bt2_shadow_runs", "run_family")
