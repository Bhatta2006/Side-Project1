"""Languages: a learner's locale and translated course content.

``users.locale`` (BCP-47, default en). ``content_translations`` holds one translation of a
concept per locale: the translated units, a hash of the source they came from (a changed source
makes it stale), how it was checked, and who reviewed it if anyone. Additive.
"""

import sqlalchemy as sa
from alembic import op

revision = "0038_locales"
down_revision = "0037_moderation_diagnostics"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("locale", sa.String(16), nullable=False, server_default="en"))
    op.create_table(
        "content_translations",
        sa.Column("concept", sa.String(160), primary_key=True),
        sa.Column("locale", sa.String(16), primary_key=True),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("units", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="machine"),
        sa.Column("model", sa.String(64), nullable=False, server_default=""),
        sa.Column("glossary_version", sa.String(16), nullable=False, server_default=""),
        sa.Column("reviewer", sa.String(80), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table("content_translations")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("locale")
