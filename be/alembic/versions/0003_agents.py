"""P2 Multimodal RAG tables — create_all handles SQLite; Alembic revision for Postgres path."""

from alembic import op

revision = "0003_agents"
down_revision = "0002_retrieval"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Explicit DDL reserved for frozen Postgres path; MVP uses metadata.create_all.
    _ = op


def downgrade() -> None:
    pass
