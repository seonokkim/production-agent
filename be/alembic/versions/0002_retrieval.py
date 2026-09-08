"""P1 schema notes — create_all handles SQLite; enable pgvector on Postgres."""

from alembic import op
import sqlalchemy as sa

revision = "0002_retrieval"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # Explicit DDL reserved for frozen Postgres path; MVP uses metadata.create_all.


def downgrade() -> None:
    pass
