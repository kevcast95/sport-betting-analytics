"""bt2_picks settlement_source (US-BE-022)

Revision ID: f1a2b3c4d5e6
Revises: e8f3a1b2c4d5
Create Date: 2026-04-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e8f3a1b2c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bt2_picks",
        sa.Column(
            "settlement_source",
            sa.String(length=32),
            nullable=False,
            server_default="user",
        ),
    )
    op.execute(
        "UPDATE bt2_picks SET settlement_source = 'user' WHERE status IN ('won','lost','void')"
    )


def downgrade() -> None:
    op.drop_column("bt2_picks", "settlement_source")
