"""The learner's colours on the account, so they follow the learner to every device. Additive.

``users.appearance`` holds "palette:mode" (for example "tide:dark"); null means the default,
Classic in light. Downgrade drops the column; browsers keep their own copy of the choice.
"""

import sqlalchemy as sa
from alembic import op

revision = "0048_user_appearance"
down_revision = "0047_generation_job_priority"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("appearance", sa.String(length=32), nullable=True))


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_column("appearance")
