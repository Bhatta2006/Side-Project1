"""Concept packages: job target and output, and generated atom packs.

Additive: three nullable or defaulted columns.
"""

import sqlalchemy as sa
from alembic import op

revision = "0024_concept_packages"
down_revision = "0023_generation_jobs"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("generation_jobs") as batch:
        batch.add_column(sa.Column("target", sa.String(80), nullable=False, server_default=""))
        batch.add_column(sa.Column("output", sa.JSON(), nullable=True))
    with op.batch_alter_table("generated_concepts") as batch:
        batch.add_column(sa.Column("atoms", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("generated_concepts") as batch:
        batch.drop_column("atoms")
    with op.batch_alter_table("generation_jobs") as batch:
        batch.drop_column("output")
        batch.drop_column("target")
