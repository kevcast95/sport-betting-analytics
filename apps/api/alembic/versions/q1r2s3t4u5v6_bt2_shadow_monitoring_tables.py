"""BT2 shadow lane persistence tables (monitor + observability, non-prod).

Revision ID: q1r2s3t4u5v6
Revises: p0a1b2c3d4e5
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "q1r2s3t4u5v6"
down_revision = "p0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bt2_shadow_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_key", sa.String(length=64), nullable=False),
        sa.Column("operating_day_key_from", sa.String(length=10), nullable=False),
        sa.Column("operating_day_key_to", sa.String(length=10), nullable=False),
        sa.Column("mode", sa.String(length=16), server_default="shadow", nullable=False),
        sa.Column("provider_stack", sa.String(length=120), nullable=False),
        sa.Column("is_shadow", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_key", name="uq_bt2_shadow_runs_run_key"),
    )
    op.create_index(
        "ix_bt2_shadow_runs_day_range",
        "bt2_shadow_runs",
        ["operating_day_key_from", "operating_day_key_to"],
        unique=False,
    )

    op.create_table(
        "bt2_shadow_provider_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("bt2_event_id", sa.Integer(), nullable=True),
        sa.Column("sm_fixture_id", sa.Integer(), nullable=True),
        sa.Column("provider_source", sa.String(length=64), nullable=False),
        sa.Column("sport_key", sa.String(length=64), nullable=True),
        sa.Column("market", sa.String(length=32), server_default="h2h", nullable=False),
        sa.Column("region", sa.String(length=16), server_default="us", nullable=False),
        sa.Column("provider_snapshot_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_last_update", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("credits_used", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["bt2_event_id"], ["bt2_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["bt2_shadow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bt2_shadow_provider_snapshots_run",
        "bt2_shadow_provider_snapshots",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_bt2_shadow_provider_snapshots_event",
        "bt2_shadow_provider_snapshots",
        ["bt2_event_id", "provider_snapshot_time"],
        unique=False,
    )

    op.create_table(
        "bt2_shadow_daily_picks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("operating_day_key", sa.String(length=10), nullable=False),
        sa.Column("bt2_event_id", sa.Integer(), nullable=True),
        sa.Column("sm_fixture_id", sa.Integer(), nullable=True),
        sa.Column("league_id", sa.Integer(), nullable=True),
        sa.Column("market", sa.String(length=32), nullable=False),
        sa.Column("selection", sa.String(length=64), nullable=True),
        sa.Column("status_shadow", sa.String(length=32), nullable=False),
        sa.Column("classification_taxonomy", sa.String(length=64), nullable=False),
        sa.Column("decimal_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("dsr_source", sa.String(length=64), nullable=True),
        sa.Column("provider_snapshot_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bt2_event_id"], ["bt2_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["league_id"], ["bt2_leagues.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["provider_snapshot_id"], ["bt2_shadow_provider_snapshots.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["bt2_shadow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bt2_shadow_daily_picks_run_day",
        "bt2_shadow_daily_picks",
        ["run_id", "operating_day_key"],
        unique=False,
    )
    op.create_index(
        "ix_bt2_shadow_daily_picks_class",
        "bt2_shadow_daily_picks",
        ["classification_taxonomy"],
        unique=False,
    )

    op.create_table(
        "bt2_shadow_pick_inputs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("shadow_daily_pick_id", sa.BigInteger(), nullable=False),
        sa.Column("input_source", sa.String(length=64), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["shadow_daily_pick_id"],
            ["bt2_shadow_daily_picks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bt2_shadow_pick_inputs_pick",
        "bt2_shadow_pick_inputs",
        ["shadow_daily_pick_id"],
        unique=False,
    )

    op.create_table(
        "bt2_shadow_pick_eval",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("shadow_daily_pick_id", sa.BigInteger(), nullable=False),
        sa.Column("eval_status", sa.String(length=32), nullable=False),
        sa.Column("classification_taxonomy", sa.String(length=64), nullable=False),
        sa.Column("eval_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["shadow_daily_pick_id"],
            ["bt2_shadow_daily_picks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shadow_daily_pick_id", name="uq_bt2_shadow_pick_eval_pick"),
    )
    op.create_index(
        "ix_bt2_shadow_pick_eval_class",
        "bt2_shadow_pick_eval",
        ["classification_taxonomy"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bt2_shadow_pick_eval_class", table_name="bt2_shadow_pick_eval")
    op.drop_table("bt2_shadow_pick_eval")
    op.drop_index("ix_bt2_shadow_pick_inputs_pick", table_name="bt2_shadow_pick_inputs")
    op.drop_table("bt2_shadow_pick_inputs")
    op.drop_index("ix_bt2_shadow_daily_picks_class", table_name="bt2_shadow_daily_picks")
    op.drop_index("ix_bt2_shadow_daily_picks_run_day", table_name="bt2_shadow_daily_picks")
    op.drop_table("bt2_shadow_daily_picks")
    op.drop_index(
        "ix_bt2_shadow_provider_snapshots_event",
        table_name="bt2_shadow_provider_snapshots",
    )
    op.drop_index(
        "ix_bt2_shadow_provider_snapshots_run",
        table_name="bt2_shadow_provider_snapshots",
    )
    op.drop_table("bt2_shadow_provider_snapshots")
    op.drop_index("ix_bt2_shadow_runs_day_range", table_name="bt2_shadow_runs")
    op.drop_table("bt2_shadow_runs")

