"""T-283 + T-288 — mapeo SM↔SofaScore y observaciones append-only SofaScore (S6.4 US-BE-062).

Revision ID: k5a6b7c8d9e0
Revises: j4a5b6c7d8e9
"""

from alembic import op
import sqlalchemy as sa


revision = "k5a6b7c8d9e0"
down_revision = "j4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bt2_nonprod_sm_sofascore_fixture_map_s64",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("operating_day_utc", sa.Date(), nullable=False),
        sa.Column("sm_fixture_id", sa.Integer(), nullable=False),
        sa.Column("kickoff_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bt2_league_id", sa.Integer(), nullable=True),
        sa.Column("home_name_norm", sa.Text(), nullable=False),
        sa.Column("away_name_norm", sa.Text(), nullable=False),
        sa.Column("sofascore_event_id", sa.Integer(), nullable=True),
        sa.Column("needs_review", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("map_note", sa.String(length=200), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bt2_league_id"], ["bt2_leagues.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sm_fixture_id",
            "operating_day_utc",
            name="uq_bt2_nonprod_sm_sofa_map_s64_sm_day",
        ),
    )
    op.create_index(
        "ix_bt2_nonprod_sm_sofa_map_s64_day",
        "bt2_nonprod_sm_sofascore_fixture_map_s64",
        ["operating_day_utc"],
        unique=False,
    )

    op.create_table(
        "bt2_nonprod_sofascore_fixture_observation_s64",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("sm_fixture_id", sa.Integer(), nullable=False),
        sa.Column("sofascore_event_id", sa.Integer(), nullable=False),
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
            name="ck_bt2_nonprod_sofa_obs_s64_lineup_avail",
        ),
    )
    op.create_index(
        "ix_bt2_nonprod_sofa_obs_s64_smfx_obs",
        "bt2_nonprod_sofascore_fixture_observation_s64",
        ["sm_fixture_id", "observed_at"],
        unique=False,
    )
    op.create_index(
        "ix_bt2_nonprod_sofa_obs_s64_ss_ev_obs",
        "bt2_nonprod_sofascore_fixture_observation_s64",
        ["sofascore_event_id", "observed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bt2_nonprod_sofa_obs_s64_ss_ev_obs", table_name="bt2_nonprod_sofascore_fixture_observation_s64")
    op.drop_index("ix_bt2_nonprod_sofa_obs_s64_smfx_obs", table_name="bt2_nonprod_sofascore_fixture_observation_s64")
    op.drop_table("bt2_nonprod_sofascore_fixture_observation_s64")
    op.drop_index("ix_bt2_nonprod_sm_sofa_map_s64_day", table_name="bt2_nonprod_sm_sofascore_fixture_map_s64")
    op.drop_table("bt2_nonprod_sm_sofascore_fixture_map_s64")
