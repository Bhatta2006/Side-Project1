"""Optional confidence on adaptive quiz answers (1 guessing .. 4 certain), for calibration.
Additive; null for every existing row.
"""

import sqlalchemy as sa
from alembic import op

revision = "0042_response_confidence"
down_revision = "0041_validation_reports"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("quiz_responses") as batch:
        batch.add_column(sa.Column("confidence", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("quiz_responses") as batch:
        batch.drop_column("confidence")
