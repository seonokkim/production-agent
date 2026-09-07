import type {
  Asset,
  DashboardMetrics,
  Generation,
  Project,
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
  dashboard: () => request<DashboardMetrics>("/api/v1/dashboard"),
  listProjects: () => request<Project[]>("/api/v1/projects"),
  getProject: (id: number) => request<Project>(`/api/v1/projects/${id}`),
  listScenes: (projectId: number) =>
    request<Scene[]>(`/api/v1/projects/${projectId}/scenes`),
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
};
