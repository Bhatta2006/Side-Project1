"""Generation recovery and provenance.

``generation_jobs.attempts`` counts runs that ended in a transient failure (provider, crash,
execution service); ``not_before`` delays the next try (backoff); ``stage`` says where a running
job is (generating, validating). A job that keeps failing ends in the dead-letter state ``dead``.
``generated_concepts.job_id`` links a released concept to the job whose log records the models,
prompt versions, inputs and sources that produced it. Additive.
"""

import sqlalchemy as sa
from alembic import op

revision = "0040_generation_recovery"
down_revision = "0039_course_maintenance"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("generation_jobs") as batch:
        batch.add_column(sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("not_before", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("stage", sa.String(16), nullable=False, server_default=""))
    with op.batch_alter_table("generated_concepts") as batch:
        batch.add_column(sa.Column("job_id", sa.String(36), nullable=True))


def downgrade():
    with op.batch_alter_table("generated_concepts") as batch:
        batch.drop_column("job_id")
    with op.batch_alter_table("generation_jobs") as batch:
        batch.drop_column("stage")
        batch.drop_column("not_before")
        batch.drop_column("attempts")
