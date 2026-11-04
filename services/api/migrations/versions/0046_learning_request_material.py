"""A learner's own material (pasted notes) on a learning request. Additive.

Wondering-style "turn my notes into a course": the notes are kept with the request so the
outline and lessons can be grounded in them. Nullable; downgrade drops the column.
"""

import sqlalchemy as sa
from alembic import op

revision = "0046_learning_request_material"
down_revision = "0045_one_open_generation_job"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("learning_requests") as batch:
        batch.add_column(sa.Column("material", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("learning_requests") as batch:
        batch.drop_column("material")
