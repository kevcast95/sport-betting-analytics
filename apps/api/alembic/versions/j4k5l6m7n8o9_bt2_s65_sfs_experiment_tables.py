"""S6.5 — tablas experimento SofaScore: odds snapshot, shadow ds_input, overrides, join audit.

Revision ID: j4k5l6m7n8o9
Revises: i3a4b5c6d7e8
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "j4k5l6m7n8o9"
down_revision = "i3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bt2_events",
        sa.Column("sofascore_event_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_bt2_events_sofascore_event_id",
        "bt2_events",
        ["sofascore_event_id"],
        unique=False,
    )

    op.create_table(
        "bt2_provider_odds_snapshot",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("bt2_event_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("source_scope", sa.String(length=32), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("canonical_version", sa.String(length=32), nullable=False, server_default="s65-v0"),
        sa.Column("provider_event_ref", sa.String(length=32), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "ingested_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bt2_event_id"], ["bt2_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bt2_event_id",
            "provider",
            "source_scope",
            "run_id",
            name="uq_bt2_provider_odds_snap_evt_prov_scope_run",
        ),
    )
    op.create_index(
        "ix_bt2_prov_odds_snap_run",
        "bt2_provider_odds_snapshot",
        ["run_id", "bt2_event_id"],
        unique=False,
    )

    op.create_table(
        "bt2_sfs_event_override",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("bt2_event_id", sa.Integer(), nullable=False),
        sa.Column("sofascore_event_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bt2_event_id"], ["bt2_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bt2_event_id", name="uq_bt2_sfs_override_event"),
    )

    op.create_table(
        "bt2_sfs_join_audit",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("bt2_event_id", sa.Integer(), nullable=False),
        sa.Column("sofascore_event_id", sa.Integer(), nullable=True),
        sa.Column("match_layer", sa.SmallInteger(), nullable=True),
        sa.Column("match_status", sa.String(length=24), nullable=False),
        sa.Column("detail_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bt2_event_id"], ["bt2_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "bt2_event_id",
            name="uq_bt2_sfs_join_audit_run_event",
        ),
    )
    op.create_index(
        "ix_bt2_sfs_join_audit_run",
        "bt2_sfs_join_audit",
        ["run_id"],
        unique=False,
    )

    op.create_table(
        "bt2_dsr_ds_input_shadow",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("bt2_event_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bt2_event_id"], ["bt2_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bt2_ds_input_shadow_run_event",
        "bt2_dsr_ds_input_shadow",
        ["run_id", "bt2_event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bt2_ds_input_shadow_run_event", table_name="bt2_dsr_ds_input_shadow")
    op.drop_table("bt2_dsr_ds_input_shadow")
    op.drop_index("ix_bt2_sfs_join_audit_run", table_name="bt2_sfs_join_audit")
    op.drop_table("bt2_sfs_join_audit")
    op.drop_table("bt2_sfs_event_override")
    op.drop_index("ix_bt2_prov_odds_snap_run", table_name="bt2_provider_odds_snapshot")
    op.drop_table("bt2_provider_odds_snapshot")
    op.drop_index("ix_bt2_events_sofascore_event_id", table_name="bt2_events")
    op.drop_column("bt2_events", "sofascore_event_id")
