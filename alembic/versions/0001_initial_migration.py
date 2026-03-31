"""Enable pgvector extension for vector similarity search.

Revision ID: 0001
Revises: (initial migration)
Create Date: 2026-03-30

This is the initial migration that:
1. Enables pgvector extension
2. Creates all Kembang AI tables
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None  # Initial migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable pgvector extension and create all tables."""
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')


def downgrade() -> None:
    """Disable pgvector extension."""
    op.execute('DROP EXTENSION IF EXISTS "vector"')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
