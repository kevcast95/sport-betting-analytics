"""bt2_vault_day_metadata: slate_band_cycle para rotar franjas al regenerar slate.

Revision ID: f2a3b4c5d6e7
Revises: c9e0f1a2b3c4
"""

from alembic import op
import sqlalchemy as sa

revision = "f2a3b4c5d6e7"
down_revision = "c9e0f1a2b3c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bt2_vault_day_metadata",
        sa.Column(
            "slate_band_cycle",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("bt2_vault_day_metadata", "slate_band_cycle")
