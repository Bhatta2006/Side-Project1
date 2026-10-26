"""Email accounts: a verified email and password on users, and emailed one-time codes.

Additive: two nullable columns, a unique index and one new table.
"""

import sqlalchemy as sa
from alembic import op

revision = "0020_email_accounts"
down_revision = "0019_playground_jobs"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("email", sa.String(254), nullable=True))
        batch.add_column(sa.Column("password_hash", sa.String(200), nullable=True))
        batch.create_unique_constraint("uq_users_email", ["email"])
    op.create_table(
        "email_codes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_email_codes_email", "email_codes", ["email"])


def downgrade():
    op.drop_table("email_codes")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_email", type_="unique")
        batch.drop_column("password_hash")
        batch.drop_column("email")
