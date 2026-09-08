"""Live OpenAI Agents SDK runner for Multimodal RAG.

Falls back to mock when the SDK is unavailable or the run fails.
Tools always hit the same approved-corpus helpers as the mock path.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agents import tools as rag_tools
from app.agents.mock_runner import STAGES
from app.agents.model_provider import should_use_live_agents
from app.config import get_settings
from app.models import AgentCitation, AgentRun, AgentRunEvent


def _emit_stages(db: Session, run: AgentRun, hits: list[rag_tools.CiteHit]) -> None:
    has_video = any(h.media_type == "video" for h in hits)
    stages = list(STAGES)
    if not has_video:
        stages = [s for s in stages if s[0] != "grounding_video"]
    for stage, en, ko in stages:
        run.stage = stage
        db.add(
            AgentRunEvent(
                agent_run_id=run.id,
                stage=stage,
                message_en=en,
                message_ko=ko,
            )
        )
        db.commit()


def _persist_hits(db: Session, run: AgentRun, hits: list[rag_tools.CiteHit]) -> None:
    for hit in hits:
        db.add(
            AgentCitation(
                agent_run_id=run.id,
                cite_key=hit.cite_key,
                asset_id=hit.asset_id,
                asset_embedding_id=hit.asset_embedding_id,
                media_type=hit.media_type,
                score=hit.score,
                snippets_json=json.dumps(hit.snippets),
                t_start=hit.t_start,
                t_end=hit.t_end,
                thumb_url=hit.thumb_url,
                poster_url=hit.poster_url,
                segment_note=hit.segment_note,
            )
        )


def _build_tools(
    db: Session,
    *,
    project_id: int | None,
    media_type: str,
    embedding_provider: str | None = None,
) -> list[Any]:
    from agents import function_tool  # type: ignore

    @function_tool
    def multimodal_search(query: str, top_n: int = 5) -> str:
        """Search approved production stills and video. Returns JSON cite cards."""
        hits = rag_tools.multimodal_search(
            db,
            query=query,
            project_id=project_id,
            media_type=media_type,
            top_n=top_n,
            embedding_provider=embedding_provider,
        )
        return rag_tools.hits_to_json(hits)

    @function_tool
    def get_asset_content(cite_key: str, mode: str = "summary") -> str:
        """Read ShotSpec / review / path metadata for a cite_key. Never invents ids."""
        return json.dumps(rag_tools.get_asset_content(db, cite_key, mode=mode), ensure_ascii=False)

    @function_tool
    def get_video_segment(
        cite_key: str,
        t_start: float | None = None,
        t_end: float | None = None,
        mode: str = "metadata",
    ) -> str:
        """Return bounded video segment descriptor + poster URL for UI."""
        return json.dumps(
            rag_tools.get_video_segment(
                db, cite_key, t_start=t_start, t_end=t_end, mode=mode
            ),
            ensure_ascii=False,
        )

    return [multimodal_search, get_asset_content, get_video_segment]


def try_run_live_agent(
    db: Session,
    run: AgentRun,
    *,
    embedding_provider: str | None = None,
) -> AgentRun | None:
    """Attempt OpenAI Agents Runner. Return None to signal mock fallback."""
    if not should_use_live_agents():
        return None

    try:
        from agents import Agent, Runner  # type: ignore
    except ImportError:
        return None

    settings = get_settings()
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key

    started = time.perf_counter()
    run.status = "running"
    run.runtime = "openai-agents"
    db.commit()

    emb = embedding_provider or run.embedding_provider or "mock"
    # Deterministic retrieval first so citations are never invented by the model.
    hits = rag_tools.multimodal_search(
        db,
        query=run.query_text,
        project_id=run.project_id,
        media_type=run.media_type,
        top_n=5,
        embedding_provider=emb,
    )
    used = getattr(rag_tools.multimodal_search, "last_embedding_used", emb)
    run.embedding_provider = str(used)
    db.commit()
    _emit_stages(db, run, hits)

    tools = _build_tools(
        db,
        project_id=run.project_id,
        media_type=run.media_type,
        embedding_provider=emb,
    )
    agent = Agent(
        name="Multimodal RAG",
        model=settings.openai_agent_model,
        instructions=(
            "You search approved production stills and video via tools only. "
            "Always cite cite_key for media claims. Distinguish image vs video. "
            "Never invent asset ids or timecodes. Never approve, reject, or generate. "
            "If tools return asset-level video matches, say so honestly."
        ),
        tools=tools,
    )

    user_input = (
        f"Query: {run.query_text}\n"
        f"media_type={run.media_type}; project_id={run.project_id}\n"
        "Use multimodal_search first, then deepen with get_asset_content / "
        "get_video_segment as needed. End with a short cited answer."
    )

    compose_note: str | None = None
    try:
        result = Runner.run_sync(agent, user_input)
        answer = str(getattr(result, "final_output", None) or result)
    except Exception as exc:  # noqa: BLE001 — fall back to deterministic compose
        compose_note = f"Live Agents run failed ({exc}); used deterministic compose"
        answer = rag_tools.compose_answer(run.query_text, hits)
        run.runtime = "openai-agents+mock-compose"

    _persist_hits(db, run, hits)
    run.answer_text = answer.strip() or rag_tools.compose_answer(run.query_text, hits)
    run.status = "completed"
    run.stage = "answering"
    run.latency_ms = int((time.perf_counter() - started) * 1000)
    run.completed_at = datetime.now(timezone.utc)
    run.error_message = compose_note
    db.commit()
    db.refresh(run)
    return run
