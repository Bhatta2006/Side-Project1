"""Course maintenance: version history of released concepts and the health of their links.

``concept_versions`` keeps every released version of a generated concept (so a revision or a
rollback never loses one and learner progress, which is keyed by concept id, is untouched).
``resource_health`` records link checks per concept and URL. Additive.
"""

import sqlalchemy as sa
from alembic import op

revision = "0039_course_maintenance"
down_revision = "0038_locales"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "concept_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_id", sa.String(80), nullable=False, index=True),
        sa.Column("concept_id", sa.String(80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("atoms", sa.JSON(), nullable=True),
        sa.Column("problems", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(40), nullable=False, server_default="update"),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_concept_versions_concept", "concept_versions", ["course_id", "concept_id"])
    op.create_table(
        "resource_health",
        sa.Column("concept", sa.String(160), primary_key=True),
        sa.Column("url", sa.String(512), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_failed_at", sa.Integer(), nullable=True),
        sa.Column("last_ok_at", sa.Integer(), nullable=True),
        sa.Column("last_checked_at", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(8), nullable=False, server_default="ok"),
    )


def downgrade():
    op.drop_table("resource_health")
    op.drop_index("ix_concept_versions_concept", table_name="concept_versions")
    op.drop_table("concept_versions")
