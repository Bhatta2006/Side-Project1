"""Moderation of shared courses and learner diagnostics.

``generated_courses.moderation`` (ok | held | removed), ``course_reports`` (one report per
learner and course), ``diagnostics`` (a short check whose answer key stays on the server).
Additive.
"""

import sqlalchemy as sa
from alembic import op

revision = "0037_moderation_diagnostics"
down_revision = "0036_course_sharing"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("generated_courses") as batch:
        batch.add_column(sa.Column("moderation", sa.String(8), nullable=False, server_default="ok"))
    op.create_table(
        "course_reports",
        sa.Column("course_id", sa.String(80), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("reason", sa.String(16), nullable=False),
        sa.Column("note", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_table(
        "diagnostics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "request_id",
            sa.String(36),
            sa.ForeignKey("learning_requests.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("model", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table("diagnostics")
    op.drop_table("course_reports")
    with op.batch_alter_table("generated_courses") as batch:
        batch.drop_column("moderation")
