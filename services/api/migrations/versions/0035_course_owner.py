"""Learner-owned generated courses.

``generated_courses.owner_id`` is set for a course a learner asked for; such a course is
visible and enrollable only by that learner. Additive.
"""

import sqlalchemy as sa
from alembic import op

revision = "0035_course_owner"
down_revision = "0034_learning_requests"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("generated_courses") as batch:
        batch.add_column(sa.Column("owner_id", sa.String(36), nullable=True))
        batch.create_index("ix_generated_courses_owner_id", ["owner_id"])


def downgrade():
    with op.batch_alter_table("generated_courses") as batch:
        batch.drop_index("ix_generated_courses_owner_id")
        batch.drop_column("owner_id")
