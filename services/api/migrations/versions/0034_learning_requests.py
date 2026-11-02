"""Learner-typed course requests ("teach me X").

One row per request: the raw text, the structured intent the parser produced (the learner can
inspect and edit it), and the generated course it led to. Unique per learner and request text,
so a double submit is one request. Additive.
"""

import sqlalchemy as sa
from alembic import op

revision = "0034_learning_requests"
down_revision = "0033_reminders"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "learning_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("text", sa.String(2000), nullable=False),
        sa.Column("intent", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False, server_default="model"),
        sa.Column("status", sa.String(24), nullable=False, server_default="parsed"),
        sa.Column("course_id", sa.String(80), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "key", name="uq_learning_request_user_key"),
    )
    op.create_index("ix_learning_requests_user_id", "learning_requests", ["user_id"])


def downgrade():
    op.drop_index("ix_learning_requests_user_id", table_name="learning_requests")
    op.drop_table("learning_requests")
