"""Weekly exams carry their own generated, execution-verified hard questions.

``weekly_assessments.generated`` maps a generated item key to the question (prompt, code,
options, answer, explanation). Additive; old attempts have none.
"""

import sqlalchemy as sa
from alembic import op

revision = "0031_weekly_generated"
down_revision = "0030_daily_counted_until"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("weekly_assessments") as batch:
        batch.add_column(sa.Column("generated", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("weekly_assessments") as batch:
        batch.drop_column("generated")
