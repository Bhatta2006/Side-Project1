"""Who resolved a learner's report, when, and whether they have seen the thank-you. Additive.

``resolved_at`` and ``resolved_by`` record the resolution (a recurring server error that comes
back clears them). ``thanks_seen_at`` stays null until the reporter dismisses the thank-you note
for a resolved report. Downgrade drops the three columns.
"""

import sqlalchemy as sa
from alembic import op

revision = "0035_report_thanks"
down_revision = "0034_launch_grants"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("error_reports") as batch:
        batch.add_column(sa.Column("resolved_at", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("resolved_by", sa.String(36), nullable=True))
        batch.add_column(sa.Column("thanks_seen_at", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("error_reports") as batch:
        batch.drop_column("thanks_seen_at")
        batch.drop_column("resolved_by")
        batch.drop_column("resolved_at")
