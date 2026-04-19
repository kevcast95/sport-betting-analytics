"""bt2_vault_standard_unlocks + bt2_vault_pick_commitment (liberar vs tomar).

Revision ID: m8n7o6p5q4
Revises: k1a2b3c4d5e6
"""

from alembic import op
import sqlalchemy as sa

revision = "m8n7o6p5q4"
down_revision = "k1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bt2_vault_standard_unlocks",
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
        sa.UniqueConstraint(
            "user_id", "daily_pick_id", name="uq_vault_standard_unlock_user_dp"
        ),
    )
    op.create_index(
        "ix_bt2_vault_standard_unlocks_user_day",
        "bt2_vault_standard_unlocks",
        ["user_id", "operating_day_key"],
        unique=False,
    )

    op.create_table(
        "bt2_vault_pick_commitment",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("daily_pick_id", sa.Integer(), nullable=False),
        sa.Column("operating_day_key", sa.String(length=10), nullable=False),
        sa.Column("commitment", sa.String(length=16), nullable=False),
        sa.Column(
            "committed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "commitment IN ('taken','not_taken')",
            name="ck_bt2_vault_pick_commitment_value",
        ),
        sa.ForeignKeyConstraint(["daily_pick_id"], ["bt2_daily_picks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["bt2_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "daily_pick_id", name="uq_vault_pick_commitment_user_dp"
        ),
    )
    op.create_index(
        "ix_bt2_vault_pick_commitment_user_day",
        "bt2_vault_pick_commitment",
        ["user_id", "operating_day_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_bt2_vault_pick_commitment_user_day", table_name="bt2_vault_pick_commitment"
    )
    op.drop_table("bt2_vault_pick_commitment")
    op.drop_index(
        "ix_bt2_vault_standard_unlocks_user_day", table_name="bt2_vault_standard_unlocks"
    )
    op.drop_table("bt2_vault_standard_unlocks")
