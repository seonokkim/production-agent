"""Initial schema — draft uses create_all on startup; Alembic reserved for Postgres path."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables are created via SQLAlchemy metadata in MVP draft lifespan.
    # Replace with explicit DDL when freezing the Postgres migration path.
    pass


def downgrade() -> None:
    pass
