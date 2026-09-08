"""P2 conversation history tables — create_all + ALTER for SQLite; Alembic for Postgres path."""

from alembic import op
import sqlalchemy as sa

revision = "0004_conversations"
down_revision = "0003_agents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False, server_default=""),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("media_type", sa.String(20), nullable=False, server_default="any"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_conversations_agent_id", "agent_conversations", ["agent_id"])

    # Nullable FK on existing agent_runs (safe if column already present via create_all path).
    with op.get_context().autocommit_block():
        bind = op.get_bind()
        insp = sa.inspect(bind)
        cols = {c["name"] for c in insp.get_columns("agent_runs")} if insp.has_table("agent_runs") else set()
        if "conversation_id" not in cols:
            op.add_column(
                "agent_runs",
                sa.Column(
                    "conversation_id",
                    sa.Integer(),
                    sa.ForeignKey("agent_conversations.id"),
                    nullable=True,
                ),
            )
            op.create_index(
                "ix_agent_runs_conversation_id", "agent_runs", ["conversation_id"]
            )

    op.create_table(
        "agent_conversation_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("agent_conversations.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("agent_run_id", sa.Integer(), sa.ForeignKey("agent_runs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_agent_conversation_messages_conversation_id",
        "agent_conversation_messages",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_table("agent_conversation_messages")
    # Keep agent_runs.conversation_id on downgrade for safety on SQLite.
    op.drop_table("agent_conversations")
