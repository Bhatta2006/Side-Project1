"""Generated course projects (Project Designer), stored with their course.

Additive: one nullable JSON column, a list of ``Project`` payloads.
"""

import sqlalchemy as sa
from alembic import op

revision = "0021_generated_projects"
down_revision = "0020_generated_problems"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("generated_courses") as batch:
        batch.add_column(sa.Column("projects", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("generated_courses") as batch:
        batch.drop_column("projects")
