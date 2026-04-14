"""bt2_pool_eligibility_audit — auditoría elegibilidad pool v1 (S6.3 T-236).

Revision ID: i3a4b5c6d7e8
Revises: h2a3b4c5d6e7
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "i3a4b5c6d7e8"
down_revision = "h2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bt2_pool_eligibility_audit",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eligibility_rule_version", sa.String(length=40), nullable=False),
        sa.Column("is_eligible", sa.Boolean(), nullable=False),
        sa.Column("primary_discard_reason", sa.String(length=64), nullable=True),
        sa.Column("detail_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["bt2_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bt2_pool_elig_audit_event_eval",
        "bt2_pool_eligibility_audit",
        ["event_id", "evaluated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bt2_pool_elig_audit_event_eval", table_name="bt2_pool_eligibility_audit")
    op.drop_table("bt2_pool_eligibility_audit")
