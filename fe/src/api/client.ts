import type {
  AgentAttachResponse,
  AgentCatalogItem,
  AgentConversation,
  AgentConversationDetail,
  AgentRun,
  Asset,
  DashboardMetrics,
  Generation,
  Project,
  ReferenceSearchResponse,
  Review,
  Scene,
  ShotSpec,
} from "../types";

const JSON_HEADERS = { "Content-Type": "application/json" };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/api/v1/health"),
  ready: () =>
    request<{
      status: string;
      generation_provider: string;
      llm_provider: string;
      embedding_provider: string;
    }>("/api/v1/ready"),
  dashboard: () => request<DashboardMetrics>("/api/v1/dashboard"),
  listProjects: () => request<Project[]>("/api/v1/projects"),
  createProject: (body: { name: string; description?: string | null }) =>
    request<Project>("/api/v1/projects", {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
    }),
  getProject: (id: number) => request<Project>(`/api/v1/projects/${id}`),
  listScenes: (projectId: number) =>
    request<Scene[]>(`/api/v1/projects/${projectId}/scenes`),
  createScene: (
    projectId: number,
    body: {
      title: string;
      episode_no?: number | null;
      scene_no?: number | null;
      brief?: string;
    },
  ) =>
    request<Scene>(`/api/v1/projects/${projectId}/scenes`, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
    }),
  getScene: (id: number) => request<Scene>(`/api/v1/scenes/${id}`),
  updateScene: (id: number, body: Partial<Scene>) =>
    request<Scene>(`/api/v1/scenes/${id}`, {
      method: "PATCH",
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
    }),
  suggestShotSpec: (sceneId: number) =>
    request<ShotSpec>(`/api/v1/scenes/${sceneId}/shot-spec/suggest`, {
      method: "POST",
    }),
  listShotSpecs: (sceneId: number) =>
    request<ShotSpec[]>(`/api/v1/scenes/${sceneId}/shot-specs`),
  saveShotSpec: (sceneId: number, body: Partial<ShotSpec>) =>
    request<ShotSpec>(`/api/v1/scenes/${sceneId}/shot-specs`, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({ ...body, source: "manual" }),
    }),
  updateShotSpec: (id: number, body: Partial<ShotSpec>) =>
    request<ShotSpec>(`/api/v1/shot-specs/${id}`, {
      method: "PATCH",
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
    }),
  submitGeneration: (
    sceneId: number,
    body: {
      generation_type: "keyframe" | "image_to_video";
      shot_spec_id: number;
      reference_asset_id?: number;
      reference_asset_embedding_id?: number;
      retrieval_event_id?: number;
      seed?: number;
      duration_seconds?: number;
    },
  ) =>
    request<{ generation_id: number; status: string }>(
      `/api/v1/scenes/${sceneId}/generations`,
      {
        method: "POST",
        headers: JSON_HEADERS,
        body: JSON.stringify(body),
      },
    ),
  getGeneration: (id: number) => request<Generation>(`/api/v1/generations/${id}`),
  listGenerations: (sceneId: number) =>
    request<Generation[]>(`/api/v1/scenes/${sceneId}/generations`),
  rerunGeneration: (id: number) =>
    request<{ generation_id: number; status: string }>(
      `/api/v1/generations/${id}/rerun`,
      { method: "POST" },
    ),
  listAssets: () => request<Asset[]>("/api/v1/assets"),
  reviewAsset: (assetId: number, decision: "approved" | "rejected", comment?: string) =>
    request<Review>(`/api/v1/assets/${assetId}/reviews`, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({ decision, comment, reviewer_name: "creator" }),
    }),
  referenceSearch: (
    sceneId: number,
    body: { query_text?: string; shot_spec_id?: number; top_k?: number },
  ) =>
    request<ReferenceSearchResponse>(`/api/v1/scenes/${sceneId}/reference-search`, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
    }),
  selectReference: (retrievalEventId: number, assetEmbeddingId: number) =>
    request(`/api/v1/retrieval-events/${retrievalEventId}/select`, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({ asset_embedding_id: assetEmbeddingId }),
    }),
  createAssetEmbedding: (assetId: number) =>
    request(`/api/v1/assets/${assetId}/embeddings`, { method: "POST" }),
  listAgents: () => request<AgentCatalogItem[]>("/api/v1/agents"),
  listAgentConversations: () =>
    request<AgentConversation[]>("/api/v1/agent-conversations"),
  createAgentConversation: (body?: {
    title?: string;
    project_id?: number | null;
    media_type?: "any" | "image" | "video";
  }) =>
    request<AgentConversationDetail>("/api/v1/agent-conversations", {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({ agent_id: "multimodal-rag", ...body }),
    }),
  getAgentConversation: (id: number) =>
    request<AgentConversationDetail>(`/api/v1/agent-conversations/${id}`),
  updateAgentConversation: (
    id: number,
    body: { title?: string; project_id?: number | null; media_type?: string },
  ) =>
    request<AgentConversationDetail>(`/api/v1/agent-conversations/${id}`, {
      method: "PATCH",
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
    }),
  deleteAgentConversation: async (id: number) => {
    const res = await fetch(`/api/v1/agent-conversations/${id}`, { method: "DELETE" });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || res.statusText);
    }
  },
  createAgentRun: (body: {
    agent_id?: string;
    query: string;
    project_id?: number | null;
    media_type?: "any" | "image" | "video";
    conversation_id?: number | null;
    embedding_provider?: "mock" | "marengo" | null;
  }) =>
    request<AgentRun>("/api/v1/agent-runs", {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({ agent_id: "multimodal-rag", ...body }),
    }),
  streamAgentRun: async (
    body: {
      agent_id?: string;
      query: string;
      project_id?: number | null;
      media_type?: "any" | "image" | "video";
      conversation_id?: number | null;
      embedding_provider?: "mock" | "marengo" | null;
    },
    handlers: {
      onStage?: (stage: {
        stage: string;
        message_en: string;
        message_ko: string;
        run_id?: number;
        conversation_id?: number;
      }) => void;
      onResult?: (run: AgentRun) => void;
      onError?: (detail: string) => void;
    },
  ): Promise<AgentRun> => {
    const res = await fetch("/api/v1/agent-runs/stream", {
      method: "POST",
      headers: { ...JSON_HEADERS, Accept: "text/event-stream" },
      body: JSON.stringify({ agent_id: "multimodal-rag", ...body }),
    });
    if (!res.ok || !res.body) {
      const detail = await res.text();
      throw new Error(detail || res.statusText);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalRun: AgentRun | null = null;
    let eventName = "message";

    const flushBlock = (block: string) => {
      const lines = block.split("\n");
      let data = "";
      for (const line of lines) {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          data += line.slice(5).trim();
        }
      }
      if (!data) return;
      const parsed = JSON.parse(data) as Record<string, unknown>;
      if (eventName === "stage" || parsed.type === "stage") {
        handlers.onStage?.({
          stage: String(parsed.stage ?? ""),
          message_en: String(parsed.message_en ?? ""),
          message_ko: String(parsed.message_ko ?? ""),
          run_id: typeof parsed.run_id === "number" ? parsed.run_id : undefined,
          conversation_id:
            typeof parsed.conversation_id === "number"
              ? parsed.conversation_id
              : undefined,
        });
      } else if (eventName === "result" || parsed.type === "result") {
        finalRun = parsed.run as AgentRun;
        handlers.onResult?.(finalRun);
      } else if (eventName === "error" || parsed.type === "error") {
        handlers.onError?.(String(parsed.detail ?? "stream error"));
      }
      eventName = "message";
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const block of parts) {
        if (block.trim()) flushBlock(block);
      }
    }
    if (buffer.trim()) flushBlock(buffer);

    if (!finalRun) {
      throw new Error("Agent stream ended without a result");
    }
    return finalRun;
  },
  getAgentRun: (id: number) => request<AgentRun>(`/api/v1/agent-runs/${id}`),
  attachAgentRun: (id: number, body: { scene_id: number; cite_keys: string[] }) =>
    request<AgentAttachResponse>(`/api/v1/agent-runs/${id}/attach`, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
    }),
};
