"""A priority on generation jobs, so a learner who is waiting is served first. Additive.

Jobs were claimed oldest first across every course: a new learner's outline and first lesson
waited behind other learners' background lessons. Lower runs first; existing jobs get the
background value. Downgrade drops the column.
"""

import sqlalchemy as sa
from alembic import op

revision = "0047_generation_job_priority"
down_revision = "0046_learning_request_material"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("generation_jobs") as batch:
        batch.add_column(sa.Column("priority", sa.Integer(), nullable=False, server_default="3"))


def downgrade():
    with op.batch_alter_table("generation_jobs") as batch:
        batch.drop_column("priority")
