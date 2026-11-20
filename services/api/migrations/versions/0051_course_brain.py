"""The course brain: subject roots, aliases, routing decisions. Additive.

``subject_roots`` / ``subject_aliases`` give every generated course a subject it belongs to;
``course_matches`` records, per learning request, which course was served or built and why.
``root_units`` hold reusable, validated teaching material per subject and topic, written from
the public ``sources`` linked in ``unit_sources``; ``concept_unit_pins`` say which unit revision
each generated lesson was written from.
New nullable columns on ``generated_courses`` (root, spec, spec key, serve) and
``enrollments`` (match id, learner plan). Downgrade drops all of it.
"""

import sqlalchemy as sa
from alembic import op

revision = "0051_course_brain"
down_revision = "0050_onboarding_drafts"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subject_roots",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("merged_into", sa.String(length=64), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_table(
        "subject_aliases",
        sa.Column("alias", sa.String(length=120), primary_key=True),
        sa.Column(
            "root_id",
            sa.String(length=64),
            sa.ForeignKey("subject_roots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_table(
        "course_matches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "request_id",
            sa.String(length=36),
            sa.ForeignKey("learning_requests.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("root_id", sa.String(length=64), nullable=True),
        sa.Column("spec", sa.JSON(), nullable=False),
        sa.Column("spec_key", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("units", sa.JSON(), nullable=False),
        sa.Column("course_id", sa.String(length=80), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("candidates", sa.JSON(), nullable=False),
        sa.Column("adaptations", sa.JSON(), nullable=False),
        sa.Column("private", sa.JSON(), nullable=False),
        sa.Column("matcher_version", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_table(
        "root_units",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "root_id",
            sa.String(length=64),
            sa.ForeignKey("subject_roots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("unit_key", sa.String(length=120), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(length=160), nullable=False),
        sa.Column("depth", sa.String(length=16), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("concepts", sa.JSON(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("quality", sa.JSON(), nullable=False),
        sa.Column("digest", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("retrieved_at", sa.Integer(), nullable=False),
        sa.Column("review_after", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("root_id", "unit_key", "revision", name="uq_root_unit_revision"),
    )
    op.create_index("ix_root_units_root_id", "root_units", ["root_id"])
    op.create_table(
        "sources",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("license", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("retrieved_at", sa.Integer(), nullable=False),
    )
    op.create_table(
        "unit_sources",
        sa.Column(
            "unit_id",
            sa.String(length=36),
            sa.ForeignKey("root_units.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "source_id",
            sa.String(length=64),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("n", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("supports", sa.String(length=400), nullable=False),
        sa.Column("retained", sa.String(length=12), nullable=False),
    )
    op.create_table(
        "concept_unit_pins",
        sa.Column("course_id", sa.String(length=80), primary_key=True),
        sa.Column("concept_id", sa.String(length=80), primary_key=True),
        sa.Column(
            "unit_id",
            sa.String(length=36),
            sa.ForeignKey("root_units.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_concept_unit_pins_unit_id", "concept_unit_pins", ["unit_id"])
    op.create_index("ix_course_matches_user_id", "course_matches", ["user_id"])
    op.create_index("ix_course_matches_course_id", "course_matches", ["course_id"])
    with op.batch_alter_table("generated_courses") as batch:
        batch.add_column(sa.Column("root_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("spec", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("spec_key", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("serve", sa.String(length=8), nullable=True))
    op.create_index("ix_generated_courses_root_id", "generated_courses", ["root_id"])
    op.create_index("ix_generated_courses_spec_key", "generated_courses", ["spec_key"])
    with op.batch_alter_table("enrollments") as batch:
        batch.add_column(sa.Column("match_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("learner_plan", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("enrollments") as batch:
        batch.drop_column("learner_plan")
        batch.drop_column("match_id")
    op.drop_index("ix_generated_courses_spec_key", table_name="generated_courses")
    op.drop_index("ix_generated_courses_root_id", table_name="generated_courses")
    with op.batch_alter_table("generated_courses") as batch:
        batch.drop_column("serve")
        batch.drop_column("spec_key")
        batch.drop_column("spec")
        batch.drop_column("root_id")
    op.drop_index("ix_course_matches_course_id", table_name="course_matches")
    op.drop_index("ix_course_matches_user_id", table_name="course_matches")
    op.drop_table("course_matches")
    op.drop_index("ix_concept_unit_pins_unit_id", table_name="concept_unit_pins")
    op.drop_table("concept_unit_pins")
    op.drop_table("unit_sources")
    op.drop_table("sources")
    op.drop_index("ix_root_units_root_id", table_name="root_units")
    op.drop_table("root_units")
    op.drop_table("subject_aliases")
    op.drop_table("subject_roots")
