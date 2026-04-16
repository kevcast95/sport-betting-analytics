"""T-287 — append-only observaciones SM intradía F3 S6.4 (no productivo).

Revision ID: j4a5b6c7d8e9
Revises: i3a4b5c6d7e8
"""

from alembic import op
import sqlalchemy as sa


revision = "j4a5b6c7d8e9"
down_revision = "i3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bt2_nonprod_sm_fixture_observation_s64",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("sm_fixture_id", sa.Integer(), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("lineup_home_usable", sa.Boolean(), nullable=False),
        sa.Column("lineup_away_usable", sa.Boolean(), nullable=False),
        sa.Column("lineup_available", sa.Boolean(), nullable=False),
        sa.Column("ft_1x2_available", sa.Boolean(), nullable=False),
        sa.Column("ou_goals_2_5_available", sa.Boolean(), nullable=False),
        sa.Column("btts_available", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "lineup_available = (lineup_home_usable AND lineup_away_usable)",
            name="ck_bt2_nonprod_sm_obs_s64_lineup_avail",
        ),
    )
    op.create_index(
        "ix_bt2_nonprod_sm_obs_s64_smfx_obs",
        "bt2_nonprod_sm_fixture_observation_s64",
        ["sm_fixture_id", "observed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_bt2_nonprod_sm_obs_s64_smfx_obs",
        table_name="bt2_nonprod_sm_fixture_observation_s64",
    )
    op.drop_table("bt2_nonprod_sm_fixture_observation_s64")
