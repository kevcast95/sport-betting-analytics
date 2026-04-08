"""bt2_picks widen stake/odds/pnl for COP bankrolls and decimal odds

Revision ID: e8f3a1b2c4d5
Revises: dc2efb49e673
Create Date: 2026-04-07

stake_units was NUMERIC(6,2) (max 9999.99); FE sends COP from bankroll * stake %,
which overflows for typical bankrolls. odds_taken NUMERIC(6,4) capped decimal odds
at 99.9999. pnl_units widened to match possible P&L on larger stakes.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8f3a1b2c4d5"
down_revision: Union[str, None] = "dc2efb49e673"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "bt2_picks",
        "odds_taken",
        existing_type=sa.Numeric(precision=6, scale=4),
        type_=sa.Numeric(precision=10, scale=4),
        existing_nullable=False,
    )
    op.alter_column(
        "bt2_picks",
        "stake_units",
        existing_type=sa.Numeric(precision=6, scale=2),
        type_=sa.Numeric(precision=14, scale=2),
        existing_nullable=False,
    )
    op.alter_column(
        "bt2_picks",
        "pnl_units",
        existing_type=sa.Numeric(precision=8, scale=2),
        type_=sa.Numeric(precision=14, scale=2),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "bt2_picks",
        "pnl_units",
        existing_type=sa.Numeric(precision=14, scale=2),
        type_=sa.Numeric(precision=8, scale=2),
        existing_nullable=True,
    )
    op.alter_column(
        "bt2_picks",
        "stake_units",
        existing_type=sa.Numeric(precision=14, scale=2),
        type_=sa.Numeric(precision=6, scale=2),
        existing_nullable=False,
    )
    op.alter_column(
        "bt2_picks",
        "odds_taken",
        existing_type=sa.Numeric(precision=10, scale=4),
        type_=sa.Numeric(precision=6, scale=4),
        existing_nullable=False,
    )
