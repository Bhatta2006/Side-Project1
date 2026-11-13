"""Notes an admin sends to a learner, shown once in the app. Additive.

``seen_at`` stays null until the learner closes the note. Rows go with the account
(``ON DELETE CASCADE``). Downgrade drops the table.
"""

import sqlalchemy as sa
from alembic import op

revision = "0036_user_notifications"
down_revision = "0035_report_thanks"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("title", sa.String(120), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sent_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("seen_at", sa.Integer(), nullable=True),
    )
    op.create_index("ix_user_notifications_user_id", "user_notifications", ["user_id"])


def downgrade():
    op.drop_index("ix_user_notifications_user_id", table_name="user_notifications")
    op.drop_table("user_notifications")
