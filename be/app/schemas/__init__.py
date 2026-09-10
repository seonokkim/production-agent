from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class SceneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    episode_no: int | None = None
    scene_no: int | None = None
    brief: str = ""


class SceneUpdate(BaseModel):
    title: str | None = None
    episode_no: int | None = None
    scene_no: int | None = None
    brief: str | None = None
    status: str | None = None


class SceneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    episode_no: int | None
    scene_no: int | None
    title: str
    brief: str
    status: str
    created_at: datetime
    updated_at: datetime


class ShotSpecBase(BaseModel):
    location: str = ""
    time_of_day: str = ""
    subjects: list[str] = Field(default_factory=list)
    action: str = ""
    shot_size: str = ""
    camera_angle: str = ""
    camera_motion: str = ""
    lighting: str = ""
    mood: str = ""
    visual_prompt: str = ""
    motion_prompt: str = ""


class ShotSpecCreate(ShotSpecBase):
    source: str = "manual"


class ShotSpecUpdate(BaseModel):
    location: str | None = None
    time_of_day: str | None = None
    subjects: list[str] | None = None
    action: str | None = None
    shot_size: str | None = None
    camera_angle: str | None = None
    camera_motion: str | None = None
    lighting: str | None = None
    mood: str | None = None
    visual_prompt: str | None = None
    motion_prompt: str | None = None


class ShotSpecRead(ShotSpecBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scene_id: int
    version: int
    source: str
    created_at: datetime


class GenerationCreate(BaseModel):
    generation_type: str = Field(pattern="^(keyframe|image_to_video)$")
    shot_spec_id: int
    reference_asset_id: int | None = None
    reference_asset_embedding_id: int | None = None
    retrieval_event_id: int | None = None
    seed: int | None = None
    duration_seconds: float | None = Field(default=4.0, ge=3.0, le=5.0)
    force_fail: bool = False


class GenerationAccepted(BaseModel):
    generation_id: int
    status: str


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    generation_job_id: int | None = None
    asset_type: str
    file_path: str
    mime_type: str
    checksum: str
    width: int | None
    height: int | None
    duration_seconds: float | None
    status: str
    created_at: datetime
    url: str | None = None
    original_filename: str | None = None
    file_size: int | None = None
    source: str | None = None
    ingestion_status: str | None = None
    extracted_text: str | None = None
    extracted_text_path: str | None = None
    metadata_json: dict[str, Any] | None = None
    processed_at: datetime | None = None


class DocumentUploadResponse(BaseModel):
    asset: AssetRead
    message: str = "Document accepted; pending ingestion"


class BatchRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pipeline_name: str
    airflow_dag_run_id: str | None
    status: str
    records_discovered: int
    records_processed: int
    records_failed: int
    started_at: datetime | None
    completed_at: datetime | None
    error_summary: str | None
    created_at: datetime


class ReviewCreate(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str | None = None
    reviewer_name: str = "creator"


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    decision: str
    comment: str | None
    reviewer_name: str
    created_at: datetime


class WorkflowVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    workflow_type: str
    version: str
    workflow_hash: str
    model_name: str
    model_version: str
    active: bool


class WorkflowGraphNode(BaseModel):
    id: str
    class_type: str
    label: str
    category: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class WorkflowGraphEdge(BaseModel):
    source: str
    source_output: int
    target: str
    target_input: str


class WorkflowGraphRead(BaseModel):
    workflow_name: str | None = None
    workflow_version: str | None = None
    workflow_type: str | None = None
    workflow_hash: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    source: str = "active"
    frozen: bool = False
    generation_id: int | None = None
    node_count: int = 0
    edge_count: int = 0
    nodes: list[WorkflowGraphNode] = Field(default_factory=list)
    edges: list[WorkflowGraphEdge] = Field(default_factory=list)
    read_only: bool = True


class GenerationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scene_id: int
    shot_spec_id: int
    workflow_version_id: int
    parent_generation_id: int | None
    provider_job_id: str | None
    generation_type: str
    provider: str
    status: str
    prompt: str
    negative_prompt: str
    model_name: str
    model_version: str
    seed: int
    width: int
    height: int
    frame_count: int | None
    fps: int | None
    duration_seconds: float | None
    reference_asset_id: int | None
    retrieval_event_id: int | None = None
    reference_asset_embedding_id: int | None = None
    workflow_snapshot_json: str
    configuration_json: str
    error_code: str | None
    error_message: str | None
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    generation_ms: int | None
    assets: list[AssetRead] = Field(default_factory=list)
    workflow_version: WorkflowVersionRead | None = None


class AssetEmbeddingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    segment_start_sec: float | None
    segment_end_sec: float | None
    model_name: str
    model_version: str
    embedding_scope: str
    created_at: datetime


class ReferenceSearchRequest(BaseModel):
    query_text: str | None = None
    shot_spec_id: int | None = None
    top_k: int = Field(default=3, ge=1, le=10)


class ReferenceSearchHit(BaseModel):
    asset_embedding_id: int
    asset_id: int
    score: float
    segment_start_sec: float | None = None
    segment_end_sec: float | None = None
    thumbnail_url: str | None = None
    camera_motion: str = ""
    lighting: str = ""
    mood: str = ""
    location: str = ""
    model_name: str = ""
    model_version: str = ""
    workflow_name: str | None = None
    workflow_hash: str | None = None
    prompt: str = ""


class ReferenceSearchResponse(BaseModel):
    retrieval_event_id: int
    query_text: str
    model_name: str
    model_version: str
    latency_ms: int | None
    results: list[ReferenceSearchHit]


class RetrievalSelectRequest(BaseModel):
    asset_embedding_id: int


class RetrievalEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scene_id: int
    query_text: str
    top_k: int
    selected_asset_embedding_id: int | None
    model_name: str
    model_version: str
    result_snapshot_json: str
    latency_ms: int | None
    created_at: datetime


class DashboardMetrics(BaseModel):
    generation_jobs: int
    approved_assets: int
    approval_rate: float
    avg_attempts_per_approval: float
    avg_generation_ms: float | None
    failed_jobs: int
    rejection_reasons: dict[str, int] = Field(default_factory=dict)
    # P1 Asset Operations
    total_assets: int = 0
    documents: int = 0
    pending_ingestion: int = 0
    failed_ingestion: int = 0
    last_airflow_run_status: str | None = None
    last_airflow_run_at: datetime | None = None
    assets_indexed: int = 0


# --- P2 Multimodal RAG (OpenAI Agents) ---


class AgentCatalogItem(BaseModel):
    agent_id: str
    type: str
    catalog_surface: str
    display_name_ko: str
    display_name_en: str
    collection_ids: list[str] = Field(default_factory=list)
    description: str = ""


class AgentRunCreate(BaseModel):
    agent_id: str = "multimodal-rag"
    query: str = Field(min_length=1)
    project_id: int | None = None
    media_type: str = Field(default="any", pattern="^(any|image|video)$")
    conversation_id: int | None = None
    embedding_provider: str | None = Field(default=None, pattern="^(mock|marengo)$")
    agent_llm_provider: str | None = Field(
        default=None, pattern="^(openai|ollama|hf|mock)$"
    )
    agent_model: str | None = None


class ShotSpecSuggestRequest(BaseModel):
    llm_provider: str | None = Field(default=None, pattern="^(openai|ollama|hf|mock)$")
    llm_model: str | None = None


class LlmOption(BaseModel):
    id: str
    label: str
    default_model: str
    notes: str = ""
    available: bool = True
    local_dir: str | None = None


class LlmOptionsResponse(BaseModel):
    default_provider: str
    default_model: str
    options: list[LlmOption]

class AgentCitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cite_key: str
    asset_id: int
    asset_embedding_id: int | None
    media_type: str
    score: float
    snippets_json: str
    t_start: float | None
    t_end: float | None
    thumb_url: str | None
    poster_url: str | None
    segment_note: str


class AgentRunEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stage: str
    message_en: str
    message_ko: str
    created_at: datetime


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: str
    conversation_id: int | None = None
    query_text: str
    project_id: int | None
    media_type: str
    embedding_provider: str = "mock"
    status: str
    stage: str
    answer_text: str
    runtime: str
    error_message: str | None
    latency_ms: int | None
    created_at: datetime
    completed_at: datetime | None
    citations: list[AgentCitationRead] = Field(default_factory=list)
    events: list[AgentRunEventRead] = Field(default_factory=list)


class AgentConversationCreate(BaseModel):
    agent_id: str = "multimodal-rag"
    title: str = ""
    project_id: int | None = None
    media_type: str = Field(default="any", pattern="^(any|image|video)$")


class AgentConversationUpdate(BaseModel):
    title: str | None = None
    project_id: int | None = None
    media_type: str | None = Field(default=None, pattern="^(any|image|video)$")


class AgentConversationMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    agent_run_id: int | None
    created_at: datetime
    agent_run: AgentRunRead | None = None


class AgentConversationRead(BaseModel):
    id: int
    agent_id: str
    title: str
    project_id: int | None
    media_type: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    preview: str = ""


class AgentConversationDetail(AgentConversationRead):
    messages: list[AgentConversationMessageRead] = Field(default_factory=list)


class AgentAttachRequest(BaseModel):
    scene_id: int
    cite_keys: list[str] = Field(min_length=1)


class AgentAttachResponse(BaseModel):
    retrieval_event_id: int
    scene_id: int
    cite_keys: list[str]
    reference_asset_ids: list[int]
    references: list[dict] = Field(default_factory=list)
