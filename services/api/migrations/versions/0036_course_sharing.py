"""Community courses: opt-in sharing of a learner's course, and creator perks.

``generated_courses.visibility`` is private until the owner agrees to share; ``credit_name`` is
the name shown if they choose to be credited. ``creator_perks`` records each reward a creator
earned (one row per user, course and tier, so a sweep is idempotent). Additive.
"""

import sqlalchemy as sa
from alembic import op

revision = "0036_course_sharing"
down_revision = "0035_course_owner"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("generated_courses") as batch:
        batch.add_column(
            sa.Column("visibility", sa.String(8), nullable=False, server_default="private")
        )
        batch.add_column(sa.Column("shared_at", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("credit_name", sa.String(80), nullable=True))
    op.create_table(
        "creator_perks",
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("course_id", sa.String(80), primary_key=True),
        sa.Column("tier", sa.String(24), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("earned_at", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_table("creator_perks")
    with op.batch_alter_table("generated_courses") as batch:
        batch.drop_column("credit_name")
        batch.drop_column("shared_at")
        batch.drop_column("visibility")
