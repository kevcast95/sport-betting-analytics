"""bt2_vault_premium_unlocks — US-BE-029 / D-05.1-002

Revision ID: a1b2c3d4e5f7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-09

Persistencia idempotente del desbloqueo premium (sin fila bt2_picks).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bt2_vault_premium_unlocks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("daily_pick_id", sa.Integer(), nullable=False),
        sa.Column("operating_day_key", sa.String(length=10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["daily_pick_id"], ["bt2_daily_picks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["bt2_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "daily_pick_id", name="uq_vault_premium_unlock_user_dp"),
    )
    op.create_index(
        "ix_bt2_vault_premium_unlocks_user_day",
        "bt2_vault_premium_unlocks",
        ["user_id", "operating_day_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bt2_vault_premium_unlocks_user_day", table_name="bt2_vault_premium_unlocks")
    op.drop_table("bt2_vault_premium_unlocks")
