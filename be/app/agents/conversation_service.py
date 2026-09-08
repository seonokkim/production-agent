"""CRUD for Multimodal RAG conversation history."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload, selectinload

from app.agents.catalog import MULTIMODAL_RAG_AGENT_ID
from app.models import AgentConversation, AgentConversationMessage, AgentRun
from app.schemas import (
    AgentCitationRead,
    AgentConversationCreate,
    AgentConversationDetail,
    AgentConversationMessageRead,
    AgentConversationRead,
    AgentConversationUpdate,
    AgentRunEventRead,
    AgentRunRead,
)


def _title_from_query(query: str) -> str:
    q = " ".join(query.strip().split())
    if len(q) <= 48:
        return q or "New chat"
    return q[:45].rstrip() + "…"


def _run_to_read(run: AgentRun) -> AgentRunRead:
    return AgentRunRead(
        id=run.id,
        agent_id=run.agent_id,
        conversation_id=run.conversation_id,
        query_text=run.query_text,
        project_id=run.project_id,
        media_type=run.media_type,
        embedding_provider=getattr(run, "embedding_provider", None) or "mock",
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


def _message_to_read(msg: AgentConversationMessage) -> AgentConversationMessageRead:
    run_read = None
    if msg.agent_run is not None:
        run_read = _run_to_read(msg.agent_run)
    return AgentConversationMessageRead(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        agent_run_id=msg.agent_run_id,
        created_at=msg.created_at,
        agent_run=run_read,
    )


def _conv_summary(conv: AgentConversation) -> AgentConversationRead:
    preview = ""
    if conv.messages:
        # prefer last user message
        for m in reversed(conv.messages):
            if m.role == "user" and m.content.strip():
                preview = m.content.strip()
                break
        if not preview:
            preview = (conv.messages[-1].content or "").strip()
    return AgentConversationRead(
        id=conv.id,
        agent_id=conv.agent_id,
        title=conv.title or preview[:48] or "New chat",
        project_id=conv.project_id,
        media_type=conv.media_type,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=len(conv.messages or []),
        preview=preview[:120],
    )


def list_conversations(db: Session, *, limit: int = 50) -> list[AgentConversationRead]:
    rows = (
        db.query(AgentConversation)
        .options(joinedload(AgentConversation.messages))
        .order_by(AgentConversation.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [_conv_summary(r) for r in rows]


def create_conversation(
    db: Session, payload: AgentConversationCreate
) -> AgentConversationDetail:
    conv = AgentConversation(
        agent_id=payload.agent_id or MULTIMODAL_RAG_AGENT_ID,
        title=(payload.title or "").strip(),
        project_id=payload.project_id,
        media_type=payload.media_type,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return get_conversation(db, conv.id)


def get_conversation(db: Session, conversation_id: int) -> AgentConversationDetail:
    conv = (
        db.query(AgentConversation)
        .options(
            selectinload(AgentConversation.messages)
            .selectinload(AgentConversationMessage.agent_run)
            .selectinload(AgentRun.citations),
            selectinload(AgentConversation.messages)
            .selectinload(AgentConversationMessage.agent_run)
            .selectinload(AgentRun.events),
        )
        .filter(AgentConversation.id == conversation_id)
        .first()
    )
    if not conv:
        raise LookupError("Conversation not found")
    summary = _conv_summary(conv)
    return AgentConversationDetail(
        **summary.model_dump(),
        messages=[_message_to_read(m) for m in (conv.messages or [])],
    )


def update_conversation(
    db: Session, conversation_id: int, payload: AgentConversationUpdate
) -> AgentConversationDetail:
    conv = db.get(AgentConversation, conversation_id)
    if not conv:
        raise LookupError("Conversation not found")
    if payload.title is not None:
        conv.title = payload.title.strip()
    if payload.project_id is not None:
        conv.project_id = payload.project_id
    if payload.media_type is not None:
        conv.media_type = payload.media_type
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    return get_conversation(db, conversation_id)


def delete_conversation(db: Session, conversation_id: int) -> None:
    conv = db.get(AgentConversation, conversation_id)
    if not conv:
        raise LookupError("Conversation not found")
    # Detach runs so delete does not cascade into provenance jobs unexpectedly.
    db.query(AgentRun).filter(AgentRun.conversation_id == conversation_id).update(
        {AgentRun.conversation_id: None}, synchronize_session=False
    )
    db.delete(conv)
    db.commit()


def ensure_conversation(
    db: Session,
    *,
    conversation_id: int | None,
    agent_id: str,
    project_id: int | None,
    media_type: str,
    first_query: str,
) -> AgentConversation:
    if conversation_id is not None:
        conv = db.get(AgentConversation, conversation_id)
        if not conv:
            raise LookupError("Conversation not found")
        return conv
    conv = AgentConversation(
        agent_id=agent_id,
        title=_title_from_query(first_query),
        project_id=project_id,
        media_type=media_type,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def append_turn(
    db: Session,
    *,
    conversation: AgentConversation,
    query: str,
    run: AgentRun,
) -> None:
    db.add(
        AgentConversationMessage(
            conversation_id=conversation.id,
            role="user",
            content=query.strip(),
            agent_run_id=None,
        )
    )
    db.add(
        AgentConversationMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=run.answer_text or "",
            agent_run_id=run.id,
        )
    )
    if not conversation.title.strip():
        conversation.title = _title_from_query(query)
    conversation.updated_at = datetime.now(timezone.utc)
    if conversation.project_id is None and run.project_id is not None:
        conversation.project_id = run.project_id
    db.commit()
