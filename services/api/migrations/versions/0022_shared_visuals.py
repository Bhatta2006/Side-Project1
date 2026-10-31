"""Shared visuals: one generated playground visual per concept, depth and language.

Additive: one new table.
"""

import sqlalchemy as sa
from alembic import op

revision = "0022_shared_visuals"
down_revision = "0021_referrals"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shared_visuals",
        sa.Column("concept", sa.String(160), primary_key=True),
        sa.Column("level", sa.String(16), primary_key=True),
        sa.Column("language", sa.String(16), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=True),
        sa.Column("artifact_id", sa.String(36), nullable=True),
        sa.Column("source_hash", sa.String(32), nullable=False, server_default=""),
        sa.Column("reports", sa.JSON(), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_shared_visuals_artifact_id", "shared_visuals", ["artifact_id"])


def downgrade():
    op.drop_index("ix_shared_visuals_artifact_id", table_name="shared_visuals")
    op.drop_table("shared_visuals")
