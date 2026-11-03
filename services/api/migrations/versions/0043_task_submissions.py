"""Task submissions: reflections, case studies and work a person judges (learn/tasks.py).
Learner data, erased with the account through the enrolment cascade. Additive.
"""

import sqlalchemy as sa
from alembic import op

revision = "0043_task_submissions"
down_revision = "0042_response_confidence"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "task_submissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "enrollment_id",
            sa.String(36),
            sa.ForeignKey("enrollments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("concept", sa.String(160), nullable=False),
        sa.Column("task_id", sa.String(80), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("text", sa.String(4000), nullable=False),
        sa.Column("link", sa.String(500), nullable=False, server_default=""),
        sa.Column("met", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, index=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("reviewer", sa.String(120), nullable=True),
        sa.Column("feedback", sa.String(2000), nullable=False, server_default=""),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("graded_at", sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_table("task_submissions")
