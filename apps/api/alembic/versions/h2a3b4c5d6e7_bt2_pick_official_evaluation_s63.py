"""bt2_pick_official_evaluation — evaluación oficial por pick sugerido (S6.3 T-227/T-228).

Revision ID: h2a3b4c5d6e7
Revises: g1a2b3c4d5e6
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "h2a3b4c5d6e7"
down_revision = "g1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bt2_pick_official_evaluation",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("daily_pick_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("market_canonical", sa.String(length=64), nullable=False),
        sa.Column("selection_canonical", sa.String(length=64), nullable=False),
        sa.Column("dsr_confidence_label", sa.String(length=32), nullable=True),
        sa.Column("suggested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "evaluation_status",
            sa.String(length=32),
            server_default="pending_result",
            nullable=False,
        ),
        sa.Column("truth_source", sa.String(length=80), nullable=True),
        sa.Column("truth_payload_ref", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("no_evaluable_reason", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["daily_pick_id"],
            ["bt2_daily_picks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["bt2_events.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("daily_pick_id", name="uq_bt2_pick_official_eval_daily_pick"),
        sa.CheckConstraint(
            "evaluation_status IN ("
            "'pending_result','evaluated_hit','evaluated_miss','void','no_evaluable'"
            ")",
            name="ck_bt2_pick_official_evaluation_status_v1",
        ),
    )
    op.create_index(
        "ix_bt2_pick_official_eval_status",
        "bt2_pick_official_evaluation",
        ["evaluation_status"],
        unique=False,
    )
    op.create_index(
        "ix_bt2_pick_official_eval_event",
        "bt2_pick_official_evaluation",
        ["event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bt2_pick_official_eval_event", table_name="bt2_pick_official_evaluation")
    op.drop_index("ix_bt2_pick_official_eval_status", table_name="bt2_pick_official_evaluation")
    op.drop_table("bt2_pick_official_evaluation")
