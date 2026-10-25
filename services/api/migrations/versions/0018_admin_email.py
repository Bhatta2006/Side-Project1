"""Admin sign-in: the verified email of an allow-listed owner account.

Additive: one nullable column. Only owner accounts ever have it set.
"""

import sqlalchemy as sa
from alembic import op

revision = "0018_admin_email"
down_revision = "0017_billing_upgrades"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("admin_email", sa.String(254), nullable=True))


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_column("admin_email")
