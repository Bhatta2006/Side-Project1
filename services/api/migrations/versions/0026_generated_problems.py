"""Generated judge problems, verified in the execution plane.

``generated_concepts.problems`` holds each concept's released problems with their tests.
``submissions.user_id`` becomes nullable: generation verifies its code as signed execution
jobs that belong to no learner (mode ``verify``).
"""

import sqlalchemy as sa
from alembic import op

revision = "0026_generated_problems"
down_revision = "0025_generation_pause"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("generated_concepts") as batch:
        batch.add_column(sa.Column("problems", sa.JSON(), nullable=True))
    with op.batch_alter_table("submissions") as batch:
        batch.alter_column("user_id", existing_type=sa.String(36), nullable=True)


def downgrade():
    op.execute("DELETE FROM submissions WHERE user_id IS NULL")
    with op.batch_alter_table("submissions") as batch:
        batch.alter_column("user_id", existing_type=sa.String(36), nullable=False)
    with op.batch_alter_table("generated_concepts") as batch:
        batch.drop_column("problems")
