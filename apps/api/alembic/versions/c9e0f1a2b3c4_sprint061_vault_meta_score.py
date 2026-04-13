"""Sprint 06.1 — metadata día vault + score completitud en daily_picks

Revision ID: c9e0f1a2b3c4
Revises: b3c4d5e6f7a8
Create Date: 2026-04-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9e0f1a2b3c4"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bt2_vault_day_metadata",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("operating_day_key", sa.String(length=10), nullable=False),
        sa.Column("dsr_signal_degraded", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("limited_coverage", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("operational_empty_hard", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("vault_empty_message_es", sa.Text(), nullable=True),
        sa.Column("fallback_disclaimer_es", sa.Text(), nullable=True),
        sa.Column(
            "future_events_in_window_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "fallback_eligible_pool_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["bt2_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "operating_day_key",
            name="uq_bt2_vault_meta_user_day",
        ),
    )
    op.create_index(
        "ix_bt2_vault_meta_user_day",
        "bt2_vault_day_metadata",
        ["user_id", "operating_day_key"],
        unique=False,
    )
    op.add_column(
        "bt2_daily_picks",
        sa.Column("data_completeness_score", sa.SmallInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bt2_daily_picks", "data_completeness_score")
    op.drop_index("ix_bt2_vault_meta_user_day", table_name="bt2_vault_day_metadata")
    op.drop_table("bt2_vault_day_metadata")
