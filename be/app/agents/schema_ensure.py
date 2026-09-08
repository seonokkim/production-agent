"""Lightweight schema ensure for conversation history (SQLite-friendly)."""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.database import Base, engine


def ensure_agent_conversation_schema() -> None:
    """create_all new tables + add missing agent_runs columns when needed."""
    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)
    if not insp.has_table("agent_runs"):
        return
    cols = {c["name"] for c in insp.get_columns("agent_runs")}
    alters: list[str] = []
    if "conversation_id" not in cols:
        alters.append(
            "ALTER TABLE agent_runs ADD COLUMN conversation_id INTEGER "
            "REFERENCES agent_conversations(id)"
        )
    if "embedding_provider" not in cols:
        alters.append(
            "ALTER TABLE agent_runs ADD COLUMN embedding_provider VARCHAR(40) "
            "NOT NULL DEFAULT 'mock'"
        )
    if not alters:
        return
    with engine.begin() as conn:
        for stmt in alters:
            conn.execute(text(stmt))
