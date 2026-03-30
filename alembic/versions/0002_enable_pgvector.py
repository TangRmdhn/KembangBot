"""Enable pgvector extension for vector similarity search."""

from alembic import op

revision = "0002"
down_revision = "0001"  # point to initial migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable pgvector extension."""
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')


def downgrade() -> None:
    """Disable pgvector extension."""
    op.execute('DROP EXTENSION IF EXISTS "vector"')
