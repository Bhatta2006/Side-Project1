"""Visual playground mode (2D sketch or 3D) per generation job.

Additive: one string column, defaulting existing rows to the sketch renderer.
"""

import sqlalchemy as sa
from alembic import op

revision = "0028_playground_mode"
down_revision = "0023_playground_shared_flag"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("playground_jobs") as batch:
        batch.add_column(sa.Column("mode", sa.String(16), nullable=False, server_default="sketch"))


def downgrade():
    with op.batch_alter_table("playground_jobs") as batch:
        batch.drop_column("mode")
