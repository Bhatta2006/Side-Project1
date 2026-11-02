"""Validation reports for generated lessons (see ``socrat.coursegen.validation``).

One row per validation round: pass, pass_with_warnings, needs_revision, human_review_required or
rejected, with structured findings. Append-only. Additive.
"""

import sqlalchemy as sa
from alembic import op

revision = "0041_validation_reports"
down_revision = "0040_generation_recovery"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "validation_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_id", sa.String(80), nullable=False, index=True),
        sa.Column("concept_id", sa.String(80), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=True),
        sa.Column("round", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(24), nullable=False, index=True),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("reviewer", sa.String(120), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("seq", sa.BigInteger(), nullable=False),
    )
    op.create_index(
        "ix_validation_reports_concept", "validation_reports", ["course_id", "concept_id"]
    )


def downgrade():
    op.drop_index("ix_validation_reports_concept", table_name="validation_reports")
    op.drop_table("validation_reports")
