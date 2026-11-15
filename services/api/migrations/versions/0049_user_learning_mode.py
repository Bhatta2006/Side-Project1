"""The learner's chosen strictness on the account. Additive.

``users.learning_mode`` holds relaxed, balanced or strict (see ``socrat.learning_mode``);
null means the default, balanced. Downgrade drops the column.
"""

import sqlalchemy as sa
from alembic import op

revision = "0049_user_learning_mode"
down_revision = "0048_user_appearance"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("learning_mode", sa.String(length=16), nullable=True))


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_column("learning_mode")
