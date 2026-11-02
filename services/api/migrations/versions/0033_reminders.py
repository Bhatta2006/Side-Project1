"""Opt-in study reminder emails.

``users.reminders`` (off by default), when the last one went out, and how many in a row have
had no study since, so the sender can go quiet. Additive.
"""

import sqlalchemy as sa
from alembic import op

revision = "0033_reminders"
down_revision = "0032_submission_recheck"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column("reminders", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(sa.Column("reminder_sent_at", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("reminders_unanswered", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_column("reminders_unanswered")
        batch.drop_column("reminder_sent_at")
        batch.drop_column("reminders")
