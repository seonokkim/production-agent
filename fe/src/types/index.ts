export type Project = {
  id: number;
  name: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type Scene = {
  id: number;
  project_id: number;
  episode_no: number | null;
  scene_no: number | null;
  title: string;
  brief: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ShotSpec = {
  id: number;
  scene_id: number;
  version: number;
  location: string;
  time_of_day: string;
  subjects: string[];
  action: string;
  shot_size: string;
  camera_angle: string;
  camera_motion: string;
  lighting: string;
  mood: string;
  visual_prompt: string;
  motion_prompt: string;
  source: string;
  created_at: string;
};

export type Asset = {
  id: number;
  generation_job_id: number;
  asset_type: string;
  file_path: string;
  mime_type: string;
  checksum: string;
  width: number | null;
  height: number | null;
  duration_seconds: number | null;
  status: string;
  created_at: string;
  url: string | null;
};

export type WorkflowVersion = {
  id: number;
  name: string;
  workflow_type: string;
  version: string;
  workflow_hash: string;
  model_name: string;
  model_version: string;
  active: boolean;
};

export type Generation = {
  id: number;
  scene_id: number;
  shot_spec_id: number;
  workflow_version_id: number;
  parent_generation_id: number | null;
  provider_job_id: string | null;
  generation_type: string;
  provider: string;
  status: string;
  prompt: string;
  negative_prompt: string;
  model_name: string;
  model_version: string;
  seed: number;
  width: number;
  height: number;
  frame_count: number | null;
  fps: number | null;
  duration_seconds: number | null;
  reference_asset_id: number | null;
  retrieval_event_id: number | null;
  reference_asset_embedding_id: number | null;
  workflow_snapshot_json: string;
  configuration_json: string;
  error_code: string | null;
  error_message: string | null;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  generation_ms: number | null;
  assets: Asset[];
  workflow_version: WorkflowVersion | null;
};

export type DashboardMetrics = {
  generation_jobs: number;
  approved_assets: number;
  approval_rate: number;
  avg_attempts_per_approval: number;
  avg_generation_ms: number | null;
  failed_jobs: number;
  rejection_reasons: Record<string, number>;
};

export type Review = {
  id: number;
  asset_id: number;
  decision: string;
  comment: string | null;
  reviewer_name: string;
  created_at: string;
};

export type ReferenceSearchHit = {
  asset_embedding_id: number;
  asset_id: number;
  score: number;
  segment_start_sec: number | null;
  segment_end_sec: number | null;
  thumbnail_url: string | null;
  camera_motion: string;
  lighting: string;
  mood: string;
  location: string;
  model_name: string;
  model_version: string;
  workflow_name: string | null;
  workflow_hash: string | null;
  prompt: string;
};

export type ReferenceSearchResponse = {
  retrieval_event_id: number;
  query_text: string;
  model_name: string;
  model_version: string;
  latency_ms: number | null;
  results: ReferenceSearchHit[];
};

export type AgentCatalogItem = {
  agent_id: string;
  type: string;
  catalog_surface: string;
  display_name_ko: string;
  display_name_en: string;
  collection_ids: string[];
  description: string;
};

export type AgentCitation = {
  id: number;
  cite_key: string;
  asset_id: number;
  asset_embedding_id: number | null;
  media_type: string;
  score: number;
  snippets_json: string;
  t_start: number | null;
  t_end: number | null;
  thumb_url: string | null;
  poster_url: string | null;
  segment_note: string;
};

export type AgentRunEvent = {
  id: number;
  stage: string;
  message_en: string;
  message_ko: string;
  created_at: string;
};

export type AgentRun = {
  id: number;
  agent_id: string;
  conversation_id: number | null;
  query_text: string;
  project_id: number | null;
  media_type: string;
  embedding_provider: string;
  status: string;
  stage: string;
  answer_text: string;
  runtime: string;
  error_message: string | null;
  latency_ms: number | null;
  created_at: string;
  completed_at: string | null;
  citations: AgentCitation[];
  events: AgentRunEvent[];
};

export type AgentConversation = {
  id: number;
  agent_id: string;
  title: string;
  project_id: number | null;
  media_type: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  preview: string;
};

export type AgentConversationMessage = {
  id: number;
  role: "user" | "assistant" | string;
  content: string;
  agent_run_id: number | null;
  created_at: string;
  agent_run: AgentRun | null;
};

export type AgentConversationDetail = AgentConversation & {
  messages: AgentConversationMessage[];
};

export type AgentAttachResponse = {
  retrieval_event_id: number;
  scene_id: number;
  cite_keys: string[];
  reference_asset_ids: number[];
  references: Array<{
    asset_id: number;
    media_type: string;
    t_start: number | null;
    t_end: number | null;
    cite_key: string;
  }>;
};
