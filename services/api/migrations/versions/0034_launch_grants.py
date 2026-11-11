"""Launch offer: free Plus for the first signups. Additive.

One row per granted slot; the slot number is the primary key so racing signups cannot share
one, the user is unique so nobody gets two, and the device is unique so one browser cannot
collect a grant per account. Downgrade drops the table.
"""

import sqlalchemy as sa
from alembic import op

revision = "0034_launch_grants"
down_revision = "0033_reminders"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "launch_grants",
        sa.Column("slot", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
        sa.Column("granted_at", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.Column("seen_at", sa.Integer(), nullable=True),
        sa.Column("device_hash", sa.String(64), nullable=True, unique=True),
    )


def downgrade():
    op.drop_table("launch_grants")
