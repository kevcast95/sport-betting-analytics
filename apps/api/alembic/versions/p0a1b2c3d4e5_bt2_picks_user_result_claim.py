"""bt2_picks: criterio manual del operador (no sustituye liquidación ni CDM).

Revision ID: p0a1b2c3d4e5
Revises: l2m3n4o5p6
"""

from alembic import op
import sqlalchemy as sa

revision = "p0a1b2c3d4e5"
down_revision = "l2m3n4o5p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bt2_picks",
        sa.Column("user_result_claim", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bt2_picks", "user_result_claim")
