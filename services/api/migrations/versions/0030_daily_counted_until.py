"""Study minutes stop double counting overlapping activities.

``daily_activity.counted_until`` is the last moment already credited today; a new credit only
covers time after it. Additive and nullable.
"""

import sqlalchemy as sa
from alembic import op

revision = "0030_daily_counted_until"
down_revision = "0029_merge_main"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("daily_activity") as batch:
        batch.add_column(sa.Column("counted_until", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("daily_activity") as batch:
        batch.drop_column("counted_until")
