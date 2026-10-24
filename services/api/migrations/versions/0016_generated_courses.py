"""Courses stored in the database for the course-generation pipeline.

Additive: two new tables only.
"""

import sqlalchemy as sa
from alembic import op

revision = "0016_generated_courses"
down_revision = "0015_passport_company_sprints"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "generated_courses",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
    )
    op.create_table(
        "generated_concepts",
        sa.Column(
            "course_id",
            sa.String(80),
            sa.ForeignKey("generated_courses.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("concept_id", sa.String(80), primary_key=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table("generated_concepts")
    op.drop_table("generated_courses")
