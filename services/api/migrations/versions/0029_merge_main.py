"""Join the course-generation/playground chain (0022-0028) with main's shared-visuals chain.

No schema change: both parents are additive and touch different columns.
"""

revision = "0029_merge_main"
down_revision = ("0028_playground_mode", "0023_playground_shared_flag")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
