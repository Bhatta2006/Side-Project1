"""Mark playground jobs that fill the shared cache, so they are not charged to one learner.

Additive: one column with a false default.
"""

import sqlalchemy as sa
from alembic import op

revision = "0023_playground_shared_flag"
down_revision = "0022_shared_visuals"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("playground_jobs") as batch:
        batch.add_column(
            sa.Column("shared", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade():
    with op.batch_alter_table("playground_jobs") as batch:
        batch.drop_column("shared")
