"""Pause course generation (budget reached or by the owner).

Additive: one defaulted column.
"""

import sqlalchemy as sa
from alembic import op

revision = "0019_generation_pause"
down_revision = "0018_concept_packages"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("generated_courses") as batch:
        batch.add_column(sa.Column("paused", sa.String(24), nullable=False, server_default=""))


def downgrade():
    with op.batch_alter_table("generated_courses") as batch:
        batch.drop_column("paused")
