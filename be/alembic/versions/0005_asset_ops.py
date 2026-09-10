"""P1 asset ops — document columns, nullable generation_job_id, batch_runs."""

from alembic import op
import sqlalchemy as sa

revision = "0005_asset_ops"
down_revision = "0004_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("batch_runs"):
        op.create_table(
            "batch_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("pipeline_name", sa.String(120), nullable=False),
            sa.Column("airflow_dag_run_id", sa.String(200), nullable=True),
            sa.Column("status", sa.String(40), nullable=False, server_default="queued"),
            sa.Column("records_discovered", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("records_failed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_batch_runs_pipeline_name", "batch_runs", ["pipeline_name"])

    if insp.has_table("assets"):
        cols = {c["name"] for c in insp.get_columns("assets")}
        additions = {
            "original_filename": sa.Column("original_filename", sa.String(255), nullable=True),
            "file_size": sa.Column("file_size", sa.Integer(), nullable=True),
            "source": sa.Column("source", sa.String(50), nullable=True),
            "ingestion_status": sa.Column("ingestion_status", sa.String(40), nullable=True),
            "extracted_text": sa.Column("extracted_text", sa.Text(), nullable=True),
            "extracted_text_path": sa.Column("extracted_text_path", sa.String(500), nullable=True),
            "metadata_json": sa.Column("metadata_json", sa.JSON(), nullable=True),
            "processed_at": sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        }
        for name, col in additions.items():
            if name not in cols:
                op.add_column("assets", col)
        if "ingestion_status" not in cols:
            op.create_index("ix_assets_ingestion_status", "assets", ["ingestion_status"])

        # Postgres: relax NOT NULL on generation_job_id for document assets.
        if bind.dialect.name == "postgresql":
            op.alter_column(
                "assets",
                "generation_job_id",
                existing_type=sa.Integer(),
                nullable=True,
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("batch_runs"):
        op.drop_index("ix_batch_runs_pipeline_name", table_name="batch_runs")
        op.drop_table("batch_runs")
    if insp.has_table("assets"):
        cols = {c["name"] for c in insp.get_columns("assets")}
        for name in [
            "processed_at",
            "metadata_json",
            "extracted_text_path",
            "extracted_text",
            "ingestion_status",
            "source",
            "file_size",
            "original_filename",
        ]:
            if name in cols:
                if name == "ingestion_status":
                    op.drop_index("ix_assets_ingestion_status", table_name="assets")
                op.drop_column("assets", name)
        if bind.dialect.name == "postgresql":
            op.alter_column(
                "assets",
                "generation_job_id",
                existing_type=sa.Integer(),
                nullable=False,
            )
