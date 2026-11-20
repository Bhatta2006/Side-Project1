"""The learner's own preferences across courses (``socrat.learner``). Additive.

``users.learner_profile`` (JSON, nullable) holds preferences that describe the person, not one
course: analogy domain, tone, explanation length, friction limit, pace, course mode, each with
who set it, plus an undo log and the tutor's pending suggestions. Downgrade drops the column.
"""

import sqlalchemy as sa
from alembic import op

revision = "0052_learner_profile"
down_revision = "0051_course_brain"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("learner_profile", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_column("learner_profile")
