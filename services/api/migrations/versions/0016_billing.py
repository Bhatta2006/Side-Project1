"""Freemium billing: a paid subscription per learner and cached Razorpay plan ids.

Additive: two new tables only. No row in `subscriptions` means the Free plan.
"""

import sqlalchemy as sa
from alembic import op

revision = "0016_billing"
down_revision = "0015_passport_company_sprints"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subscriptions",
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("plan", sa.String(16), nullable=False),
        sa.Column("interval", sa.String(8), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("razorpay_subscription_id", sa.String(64), nullable=False, unique=True),
        sa.Column("current_end", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.Integer(), nullable=False),
    )
    op.create_table(
        "billing_plans",
        sa.Column("key", sa.String(32), primary_key=True),
        sa.Column("razorpay_plan_id", sa.String(64), nullable=False),
    )


def downgrade():
    op.drop_table("billing_plans")
    op.drop_table("subscriptions")
