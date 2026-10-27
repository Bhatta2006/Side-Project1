"""Referrals: a share code on users, who referred whom, and the ladder rewards earned.

Additive: one nullable column with a unique index and two new tables.
"""

import sqlalchemy as sa
from alembic import op

revision = "0021_referrals"
down_revision = "0020_email_accounts"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("referral_code", sa.String(12), nullable=True))
        batch.create_unique_constraint("uq_users_referral_code", ["referral_code"])
    op.create_table(
        "referrals",
        sa.Column(
            "friend_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "referrer_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_referrals_referrer_id", "referrals", ["referrer_id"])
    op.create_table(
        "referral_rewards",
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("rung", sa.String(48), primary_key=True),
        sa.Column("earned_at", sa.Integer(), nullable=False),
        sa.Column("granted_at", sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_table("referral_rewards")
    op.drop_table("referrals")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_referral_code", type_="unique")
        batch.drop_column("referral_code")
