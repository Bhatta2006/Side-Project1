"""A browser-judged submit is re-run natively before it earns credit.

``submissions.recheck_of`` points a native re-run job at the browser submission it confirms.
Additive; every existing row has none.
"""

import sqlalchemy as sa
from alembic import op

revision = "0032_submission_recheck"
down_revision = "0031_weekly_generated"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("submissions") as batch:
        batch.add_column(sa.Column("recheck_of", sa.String(length=36), nullable=True))
        batch.create_index("ix_submissions_recheck_of", ["recheck_of"])


def downgrade():
    with op.batch_alter_table("submissions") as batch:
        batch.drop_index("ix_submissions_recheck_of")
        batch.drop_column("recheck_of")
