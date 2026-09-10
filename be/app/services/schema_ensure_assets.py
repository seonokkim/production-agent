"""Ensure document/ingestion columns + batch_runs; nullable generation_job_id on SQLite."""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text

from app.database import Base, engine

logger = logging.getLogger(__name__)

_ASSET_COLUMNS: dict[str, str] = {
    "original_filename": "ALTER TABLE assets ADD COLUMN original_filename VARCHAR(255)",
    "file_size": "ALTER TABLE assets ADD COLUMN file_size INTEGER",
    "source": "ALTER TABLE assets ADD COLUMN source VARCHAR(50)",
    "ingestion_status": "ALTER TABLE assets ADD COLUMN ingestion_status VARCHAR(40)",
    "extracted_text": "ALTER TABLE assets ADD COLUMN extracted_text TEXT",
    "extracted_text_path": "ALTER TABLE assets ADD COLUMN extracted_text_path VARCHAR(500)",
    "metadata_json": "ALTER TABLE assets ADD COLUMN metadata_json JSON",
    "processed_at": "ALTER TABLE assets ADD COLUMN processed_at DATETIME",
}


def _sqlite_generation_job_id_not_null(conn) -> bool:
    rows = conn.execute(text("PRAGMA table_info(assets)")).fetchall()
    for row in rows:
        # (cid, name, type, notnull, dflt_value, pk)
        if row[1] == "generation_job_id":
            return bool(row[3])
    return False


def _sqlite_rebuild_assets_nullable_job(conn) -> None:
    """Rebuild assets so generation_job_id can be NULL (document uploads)."""
    logger.info("Rebuilding assets table to allow nullable generation_job_id")
    conn.execute(text("PRAGMA foreign_keys=OFF"))
    conn.execute(
        text(
            """
            CREATE TABLE assets_new (
                id INTEGER NOT NULL PRIMARY KEY,
                generation_job_id INTEGER,
                asset_type VARCHAR(50) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                mime_type VARCHAR(100) NOT NULL,
                checksum VARCHAR(64) NOT NULL,
                width INTEGER,
                height INTEGER,
                duration_seconds FLOAT,
                status VARCHAR(50) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                original_filename VARCHAR(255),
                file_size INTEGER,
                source VARCHAR(50),
                ingestion_status VARCHAR(40),
                extracted_text TEXT,
                extracted_text_path VARCHAR(500),
                metadata_json JSON,
                processed_at DATETIME,
                FOREIGN KEY(generation_job_id) REFERENCES generation_jobs (id)
            )
            """
        )
    )
    # Copy overlapping columns from old table.
    old_cols = {
        r[1] for r in conn.execute(text("PRAGMA table_info(assets)")).fetchall()
    }
    copy_cols = [
        c
        for c in [
            "id",
            "generation_job_id",
            "asset_type",
            "file_path",
            "mime_type",
            "checksum",
            "width",
            "height",
            "duration_seconds",
            "status",
            "created_at",
            "original_filename",
            "file_size",
            "source",
            "ingestion_status",
            "extracted_text",
            "extracted_text_path",
            "metadata_json",
            "processed_at",
        ]
        if c in old_cols
    ]
    cols_sql = ", ".join(copy_cols)
    conn.execute(text(f"INSERT INTO assets_new ({cols_sql}) SELECT {cols_sql} FROM assets"))
    conn.execute(text("DROP TABLE assets"))
    conn.execute(text("ALTER TABLE assets_new RENAME TO assets"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_assets_generation_job_id ON assets (generation_job_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_assets_ingestion_status ON assets (ingestion_status)"))
    conn.execute(text("PRAGMA foreign_keys=ON"))


def ensure_asset_ops_schema() -> None:
    """create_all new tables + add missing assets columns when needed."""
    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)
    if not insp.has_table("assets"):
        return
    cols = {c["name"] for c in insp.get_columns("assets")}
    alters = [stmt for name, stmt in _ASSET_COLUMNS.items() if name not in cols]

    dialect = engine.dialect.name
    with engine.begin() as conn:
        for stmt in alters:
            conn.execute(text(stmt))
        if dialect == "sqlite" and _sqlite_generation_job_id_not_null(conn):
            _sqlite_rebuild_assets_nullable_job(conn)
