"""Agent run orchestration — mock + optional live OpenAI Agents Runner."""

from __future__ import annotations

import json
from collections.abc import Iterator

from sqlalchemy.orm import Session, joinedload

from app.agents import conversation_service
from app.agents.catalog import MULTIMODAL_RAG_AGENT_ID, get_agent
from app.agents.live_runner import try_run_live_agent
from app.agents.mock_runner import STAGES, run_mock_agent
from app.agents.model_provider import resolve_runtime_label, should_use_live_agents
from app.agents.multimodal_rag_factory import MultimodalRagAgentFactory
from app.config import get_settings
from app.models import AgentRun, RetrievalEvent, Scene
from app.schemas import (
    AgentAttachResponse,
    AgentCitationRead,
    AgentRunCreate,
    AgentRunEventRead,
    AgentRunRead,
)


def _to_read(run: AgentRun) -> AgentRunRead:
    return AgentRunRead(
        id=run.id,
        agent_id=run.agent_id,
        conversation_id=run.conversation_id,
        query_text=run.query_text,
        project_id=run.project_id,
        media_type=run.media_type,
        embedding_provider=run.embedding_provider,
        status=run.status,
        stage=run.stage,
        answer_text=run.answer_text,
        runtime=run.runtime,
        error_message=run.error_message,
        latency_ms=run.latency_ms,
        created_at=run.created_at,
        completed_at=run.completed_at,
        citations=[AgentCitationRead.model_validate(c) for c in (run.citations or [])],
        events=[AgentRunEventRead.model_validate(e) for e in (run.events or [])],
    )


def get_run(db: Session, run_id: int) -> AgentRunRead:
    run = (
        db.query(AgentRun)
        .options(joinedload(AgentRun.citations), joinedload(AgentRun.events))
        .filter(AgentRun.id == run_id)
        .first()
    )
    if not run:
        raise LookupError("Agent run not found")
    return _to_read(run)


def create_and_execute(db: Session, payload: AgentRunCreate) -> AgentRunRead:
    catalog = get_agent(payload.agent_id)
    if not catalog:
        raise LookupError(f"Unknown agent_id: {payload.agent_id}")
    if payload.agent_id != MULTIMODAL_RAG_AGENT_ID:
        raise ValueError("Only multimodal-rag is supported in MVP")

    runtime = resolve_runtime_label()
    MultimodalRagAgentFactory.create(
        runtime=runtime if should_use_live_agents() else "mock",
        db=db if should_use_live_agents() else None,
        project_id=payload.project_id,
        media_type=payload.media_type,
    )

    conv = conversation_service.ensure_conversation(
        db,
        conversation_id=payload.conversation_id,
        agent_id=payload.agent_id,
        project_id=payload.project_id,
        media_type=payload.media_type,
        first_query=payload.query,
    )

    settings = get_settings()
    emb_choice = (payload.embedding_provider or settings.embedding_provider or "mock").strip().lower()
    if emb_choice in {"twelvelabs", "twelve_labs", "twelve-labs"}:
        emb_choice = "marengo"

    run = AgentRun(
        agent_id=payload.agent_id,
        conversation_id=conv.id,
        query_text=payload.query.strip(),
        project_id=payload.project_id,
        media_type=payload.media_type,
        embedding_provider=emb_choice,
        status="queued",
        stage="queued",
        runtime=runtime,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    live = (
        try_run_live_agent(db, run, embedding_provider=emb_choice)
        if should_use_live_agents()
        else None
    )
    if live is None:
        run_mock_agent(db, run, embedding_provider=emb_choice)

    # Reload for answer_text after execution
    db.refresh(run)
    conversation_service.append_turn(
        db, conversation=conv, query=payload.query, run=run
    )
    return get_run(db, run.id)


def create_execute_sse(db: Session, payload: AgentRunCreate) -> Iterator[str]:
    """Create run, execute, stream SSE-formatted stage + result events."""
    result = create_and_execute(db, payload)
    for event in result.events:
        data = json.dumps(
            {
                "type": "stage",
                "run_id": result.id,
                "conversation_id": result.conversation_id,
                "stage": event.stage,
                "message_en": event.message_en,
                "message_ko": event.message_ko,
            },
            ensure_ascii=False,
        )
        yield f"event: stage\ndata: {data}\n\n"

    final = json.dumps({"type": "result", "run": result.model_dump(mode="json")}, ensure_ascii=False)
    yield f"event: result\ndata: {final}\n\n"


def attach_to_scene(
    db: Session, run_id: int, scene_id: int, cite_keys: list[str]
) -> AgentAttachResponse:
    run = (
        db.query(AgentRun)
        .options(joinedload(AgentRun.citations))
        .filter(AgentRun.id == run_id)
        .first()
    )
    if not run:
        raise LookupError("Agent run not found")
    if run.status != "completed":
        raise ValueError("Only completed agent runs can attach citations")

    scene = db.get(Scene, scene_id)
    if not scene:
        raise LookupError("Scene not found")

    wanted = set(cite_keys)
    cites = [c for c in run.citations if c.cite_key in wanted]
    if not cites:
        raise ValueError("No matching cite_keys on this run")
    missing = wanted - {c.cite_key for c in cites}
    if missing:
        raise ValueError(f"Unknown cite_keys: {sorted(missing)}")

    snapshot = []
    references = []
    asset_ids: list[int] = []
    selected_emb: int | None = None

    for c in cites:
        asset_ids.append(c.asset_id)
        if selected_emb is None and c.asset_embedding_id is not None:
            selected_emb = c.asset_embedding_id
        snapshot.append(
            {
                "cite_key": c.cite_key,
                "asset_id": c.asset_id,
                "asset_embedding_id": c.asset_embedding_id,
                "media_type": c.media_type,
                "score": c.score,
                "t_start": c.t_start,
                "t_end": c.t_end,
            }
        )
        references.append(
            {
                "asset_id": c.asset_id,
                "media_type": c.media_type,
                "t_start": c.t_start,
                "t_end": c.t_end,
                "cite_key": c.cite_key,
            }
        )

    event = RetrievalEvent(
        scene_id=scene_id,
        query_text=run.query_text,
        top_k=len(cites),
        selected_asset_embedding_id=selected_emb,
        model_name=f"agent:{run.agent_id}",
        model_version=run.runtime,
        result_snapshot_json=json.dumps(snapshot),
        latency_ms=run.latency_ms,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return AgentAttachResponse(
        retrieval_event_id=event.id,
        scene_id=scene_id,
        cite_keys=[c.cite_key for c in cites],
        reference_asset_ids=asset_ids,
        references=references,
    )


PROGRESS_STAGES = STAGES
