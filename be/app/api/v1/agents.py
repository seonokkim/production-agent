from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents import catalog as agent_catalog
from app.agents import conversation_service, run_service
from app.database import get_db
from app.schemas import (
    AgentAttachRequest,
    AgentAttachResponse,
    AgentCatalogItem,
    AgentConversationCreate,
    AgentConversationDetail,
    AgentConversationRead,
    AgentConversationUpdate,
    AgentRunCreate,
    AgentRunRead,
)

router = APIRouter(tags=["agents"])


@router.get("/agents", response_model=list[AgentCatalogItem])
def list_agents():
    return agent_catalog.list_agents()


@router.get("/agents/{agent_id}", response_model=AgentCatalogItem)
def get_agent(agent_id: str):
    item = agent_catalog.get_agent(agent_id)
    if not item:
        raise HTTPException(status_code=404, detail="Agent not found")
    return item


@router.get("/agent-conversations", response_model=list[AgentConversationRead])
def list_agent_conversations(db: Session = Depends(get_db)):
    return conversation_service.list_conversations(db)


@router.post(
    "/agent-conversations",
    response_model=AgentConversationDetail,
    status_code=201,
)
def create_agent_conversation(
    payload: AgentConversationCreate, db: Session = Depends(get_db)
):
    return conversation_service.create_conversation(db, payload)


@router.get(
    "/agent-conversations/{conversation_id}",
    response_model=AgentConversationDetail,
)
def get_agent_conversation(conversation_id: int, db: Session = Depends(get_db)):
    try:
        return conversation_service.get_conversation(db, conversation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch(
    "/agent-conversations/{conversation_id}",
    response_model=AgentConversationDetail,
)
def patch_agent_conversation(
    conversation_id: int,
    payload: AgentConversationUpdate,
    db: Session = Depends(get_db),
):
    try:
        return conversation_service.update_conversation(db, conversation_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/agent-conversations/{conversation_id}", status_code=204)
def delete_agent_conversation(conversation_id: int, db: Session = Depends(get_db)):
    try:
        conversation_service.delete_conversation(db, conversation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/agent-runs", response_model=AgentRunRead, status_code=201)
def create_agent_run(payload: AgentRunCreate, db: Session = Depends(get_db)):
    """JSON poll path — create + execute Multimodal RAG run (persists into conversation)."""
    try:
        return run_service.create_and_execute(db, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/agent-runs/stream")
def create_agent_run_stream(payload: AgentRunCreate, db: Session = Depends(get_db)):
    """SSE path — stages then final result."""
    import json

    if not agent_catalog.get_agent(payload.agent_id):
        raise HTTPException(status_code=404, detail=f"Unknown agent_id: {payload.agent_id}")

    def event_gen():
        try:
            yield from run_service.create_execute_sse(db, payload)
        except (LookupError, ValueError) as exc:
            err = json.dumps({"type": "error", "detail": str(exc)}, ensure_ascii=False)
            yield f"event: error\ndata: {err}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agent-runs/{run_id}", response_model=AgentRunRead)
def get_agent_run(run_id: int, db: Session = Depends(get_db)):
    try:
        return run_service.get_run(db, run_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/agent-runs/{run_id}/attach",
    response_model=AgentAttachResponse,
    status_code=201,
)
def attach_agent_run(
    run_id: int, payload: AgentAttachRequest, db: Session = Depends(get_db)
):
    try:
        return run_service.attach_to_scene(db, run_id, payload.scene_id, payload.cite_keys)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
