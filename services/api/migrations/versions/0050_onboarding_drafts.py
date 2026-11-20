"""Lesson 0 onboarding drafts. Additive.

``onboarding_drafts`` holds a visitor's goal, choices, generated calibration (with its answer
keys) and the observed answers until they sign in and claim it. Downgrade drops the table.
"""

import sqlalchemy as sa
from alembic import op

revision = "0050_onboarding_drafts"
down_revision = "0049_user_learning_mode"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "onboarding_drafts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("intent", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("doors", sa.JSON(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=True),
        sa.Column("door", sa.String(length=80), nullable=True),
        sa.Column("calibration", sa.JSON(), nullable=True),
        sa.Column("signals", sa.JSON(), nullable=False),
        sa.Column("profile", sa.JSON(), nullable=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "request_id",
            sa.String(length=36),
            sa.ForeignKey("learning_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_onboarding_drafts_user_id", "onboarding_drafts", ["user_id"])


def downgrade():
    op.drop_index("ix_onboarding_drafts_user_id", table_name="onboarding_drafts")
    op.drop_table("onboarding_drafts")
