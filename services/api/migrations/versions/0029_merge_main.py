"""Join the course-generation chain (0022-0027) with main's shared-visuals and playground-mode chain (0022-0023, 0028).

No schema change: both parents are additive and touch different columns.
"""

revision = "0029_merge_main"
down_revision = ("0027_generated_projects", "0028_playground_mode")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
