"""Billing: a pending upgrade on the subscription, and room for price-keyed plan ids.

Additive: one nullable column and a wider key.
"""

import sqlalchemy as sa
from alembic import op

revision = "0017_billing_upgrades"
down_revision = "0016_billing"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("subscriptions") as batch:
        batch.add_column(sa.Column("pending", sa.String(96), nullable=True))
    with op.batch_alter_table("billing_plans") as batch:
        batch.alter_column("key", existing_type=sa.String(32), type_=sa.String(48))


def downgrade():
    with op.batch_alter_table("billing_plans") as batch:
        batch.alter_column("key", existing_type=sa.String(48), type_=sa.String(32))
    with op.batch_alter_table("subscriptions") as batch:
        batch.drop_column("pending")
