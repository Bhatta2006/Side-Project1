"""Generated pictures for lesson sections (``coursegen/illustrate.py``). Additive.

``lesson_illustrations`` holds one image per planned lesson section: the bytes (a few hundred
KB), its caption and alt text as an image check described them, and which model drew it.
Downgrade drops the table.
"""

import sqlalchemy as sa
from alembic import op

revision = "0053_lesson_illustrations"
down_revision = "0052_learner_profile"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "lesson_illustrations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_id", sa.String(80), nullable=False),
        sa.Column("concept_id", sa.String(80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(200), nullable=False),
        sa.Column("caption", sa.String(300), nullable=False),
        sa.Column("alt", sa.String(600), nullable=False),
        sa.Column("mime", sa.String(40), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_lesson_illustrations_concept",
        "lesson_illustrations",
        ["course_id", "concept_id", "version"],
    )


def downgrade():
    op.drop_index("ix_lesson_illustrations_concept", table_name="lesson_illustrations")
    op.drop_table("lesson_illustrations")
