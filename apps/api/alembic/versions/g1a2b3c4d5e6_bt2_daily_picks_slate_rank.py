"""bt2_daily_picks: slate_rank para orden cartelera (5 visibles de hasta 20 persistidos).

Revision ID: g1a2b3c4d5e6
Revises: f2a3b4c5d6e7
"""

from alembic import op
import sqlalchemy as sa

revision = "g1a2b3c4d5e6"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bt2_daily_picks",
        sa.Column("slate_rank", sa.SmallInteger(), nullable=True),
    )
    op.execute(
        """
        WITH numbered AS (
            SELECT id,
                ROW_NUMBER() OVER (
                    PARTITION BY user_id, operating_day_key
                    ORDER BY
                        CASE access_tier WHEN 'standard' THEN 1 ELSE 2 END,
                        suggested_at ASC
                ) AS rn
            FROM bt2_daily_picks
        )
        UPDATE bt2_daily_picks d
        SET slate_rank = n.rn
        FROM numbered n
        WHERE d.id = n.id
        """
    )
    op.alter_column(
        "bt2_daily_picks",
        "slate_rank",
        existing_type=sa.SmallInteger(),
        nullable=False,
        server_default="1",
    )
    op.create_index(
        "ix_daily_picks_user_day_slate_rank",
        "bt2_daily_picks",
        ["user_id", "operating_day_key", "slate_rank"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_daily_picks_user_day_slate_rank", table_name="bt2_daily_picks")
    op.drop_column("bt2_daily_picks", "slate_rank")
