from datetime import datetime

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
    seed: int | None = None
    duration_seconds: float | None = Field(default=4.0, ge=3.0, le=5.0)
    force_fail: bool = False


class GenerationAccepted(BaseModel):
    generation_id: int
    status: str


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    generation_job_id: int
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


class DashboardMetrics(BaseModel):
    generation_jobs: int
    approved_assets: int
    approval_rate: float
    avg_attempts_per_approval: float
    avg_generation_ms: float | None
    failed_jobs: int
    rejection_reasons: dict[str, int] = Field(default_factory=dict)
