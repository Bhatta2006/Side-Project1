"""Course-generation jobs, and review status plus brief on generated courses.

Additive: one new table and two columns (existing generated courses stay published).
"""

import sqlalchemy as sa
from alembic import op

revision = "0023_generation_jobs"
down_revision = "0022_generated_courses"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("generated_courses") as batch:
        batch.add_column(
            sa.Column("status", sa.String(16), nullable=False, server_default="published")
        )
        batch.add_column(sa.Column("brief", sa.JSON(), nullable=True))
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("course_id", sa.String(80), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("log", sa.JSON(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("error", sa.String(500), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_generation_jobs_course_id", "generation_jobs", ["course_id"])
    op.create_index("ix_generation_jobs_state", "generation_jobs", ["state"])


def downgrade():
    op.drop_index("ix_generation_jobs_state", "generation_jobs")
    op.drop_index("ix_generation_jobs_course_id", "generation_jobs")
    op.drop_table("generation_jobs")
    with op.batch_alter_table("generated_courses") as batch:
        batch.drop_column("brief")
        batch.drop_column("status")
