"""Playground jobs: visual generation runs in the worker, not inside the learner's request.

Additive: one new table.
"""

import sqlalchemy as sa
from alembic import op

revision = "0019_playground_jobs"
down_revision = "0018_admin_email"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "playground_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "thread_id",
            sa.String(36),
            sa.ForeignKey("assistant_threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("language", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("progress", sa.JSON(), nullable=False),
        sa.Column("error", sa.String(64), nullable=False),
        sa.Column("tries", sa.Integer(), nullable=False),
        sa.Column("heartbeat_at", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_playground_jobs_user_id", "playground_jobs", ["user_id"])
    op.create_index("ix_playground_jobs_status", "playground_jobs", ["status", "created_at"])


def downgrade():
    op.drop_table("playground_jobs")
