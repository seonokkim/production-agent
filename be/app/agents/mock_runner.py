"""Deterministic Multimodal RAG mock runner (no OpenAI key required)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agents import tools as rag_tools
from app.models import AgentCitation, AgentRun, AgentRunEvent

STAGES = [
    ("searching", "Searching approved image/video", "승인 이미지·영상 검색 중"),
    ("reading", "Reading candidate assets", "후보 자산 메타 확인 중"),
    ("grounding_video", "Grounding video segments", "영상 구간·포스터 정리 중"),
    ("answering", "Composing cited answer", "근거 기반 답변 작성 중"),
]


def run_mock_agent(
    db: Session,
    run: AgentRun,
    *,
    top_n: int = 5,
    embedding_provider: str | None = None,
) -> AgentRun:
    """Execute mock multimodal search and persist stages + citations."""
    started = time.perf_counter()
    run.status = "running"
    run.runtime = "mock"
    db.commit()

    emb = embedding_provider or run.embedding_provider or "mock"
    hits = rag_tools.multimodal_search(
        db,
        query=run.query_text,
        project_id=run.project_id,
        media_type=run.media_type,
        top_n=top_n,
        embedding_provider=emb,
    )
    used = getattr(rag_tools.multimodal_search, "last_embedding_used", emb)
    run.embedding_provider = str(used)
    has_video = any(h.media_type == "video" for h in hits)
    stages_to_emit = list(STAGES)
    if not has_video:
        stages_to_emit = [s for s in stages_to_emit if s[0] != "grounding_video"]

    for stage, en, ko in stages_to_emit:
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

    run.answer_text = rag_tools.compose_answer(run.query_text, hits)
    run.status = "completed"
    run.stage = "answering"
    run.latency_ms = int((time.perf_counter() - started) * 1000)
    run.completed_at = datetime.now(timezone.utc)
    run.error_message = None
    db.commit()
    db.refresh(run)
    return run
