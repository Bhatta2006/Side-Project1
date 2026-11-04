"""Visible revisions of a generated course's plan (coursegen/evolve.py). Additive."""

import sqlalchemy as sa
from alembic import op

revision = "0044_course_revisions"
down_revision = "0043_task_submissions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "course_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_id", sa.String(80), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("change", sa.String(300), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table("course_revisions")
