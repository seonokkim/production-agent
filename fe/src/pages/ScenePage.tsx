import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Generation, ShotSpec } from "../types";

const emptySpec: Omit<ShotSpec, "id" | "scene_id" | "version" | "source" | "created_at"> = {
  location: "",
  time_of_day: "",
  subjects: [],
  action: "",
  shot_size: "",
  camera_angle: "",
  camera_motion: "",
  lighting: "",
  mood: "",
  visual_prompt: "",
  motion_prompt: "",
};

export function ScenePage() {
  const { id } = useParams();
  const sceneId = Number(id);
  const qc = useQueryClient();

  const scene = useQuery({
    queryKey: ["scene", sceneId],
    queryFn: () => api.getScene(sceneId),
    enabled: Number.isFinite(sceneId),
  });
  const project = useQuery({
    queryKey: ["project", scene.data?.project_id],
    queryFn: () => api.getProject(scene.data!.project_id),
    enabled: !!scene.data?.project_id,
  });
  const specs = useQuery({
    queryKey: ["shot-specs", sceneId],
    queryFn: () => api.listShotSpecs(sceneId),
    enabled: Number.isFinite(sceneId),
  });
  const generations = useQuery({
    queryKey: ["generations", sceneId],
    queryFn: () => api.listGenerations(sceneId),
    enabled: Number.isFinite(sceneId),
    refetchInterval: (query) => {
      const data = query.state.data as Generation[] | undefined;
      const busy = data?.some((g) => g.status === "queued" || g.status === "running");
      return busy ? 2000 : false;
    },
  });

  const [brief, setBrief] = useState("");
  const [draft, setDraft] = useState(emptySpec);
  const [rejectComment, setRejectComment] = useState("");
  const [activeGenId, setActiveGenId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (scene.data) setBrief(scene.data.brief);
  }, [scene.data]);

  useEffect(() => {
    const latest = specs.data?.[0];
    if (latest) {
      setDraft({
        location: latest.location,
        time_of_day: latest.time_of_day,
        subjects: latest.subjects,
        action: latest.action,
        shot_size: latest.shot_size,
        camera_angle: latest.camera_angle,
        camera_motion: latest.camera_motion,
        lighting: latest.lighting,
        mood: latest.mood,
        visual_prompt: latest.visual_prompt,
        motion_prompt: latest.motion_prompt,
      });
    }
  }, [specs.data]);

  const latestSpec = specs.data?.[0];
  const keyframes = useMemo(
    () =>
      (generations.data || []).filter(
        (g) => g.generation_type === "keyframe" && g.status === "completed",
      ),
    [generations.data],
  );
  const selectedKeyframe = keyframes[0];
  const videos = useMemo(
    () =>
      (generations.data || []).filter((g) => g.generation_type === "image_to_video"),
    [generations.data],
  );
  const activeGen =
    (generations.data || []).find((g) => g.id === activeGenId) ||
    videos[0] ||
    selectedKeyframe ||
    null;
  const activeAsset = activeGen?.assets[0];

  const saveBrief = useMutation({
    mutationFn: () => api.updateScene(sceneId, { brief }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scene", sceneId] }),
  });

  const suggest = useMutation({
    mutationFn: async () => {
      await api.updateScene(sceneId, { brief });
      return api.suggestShotSpec(sceneId);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["shot-specs", sceneId] });
      setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });

  const saveSpec = useMutation({
    mutationFn: () => api.saveShotSpec(sceneId, { ...draft, subjects: draft.subjects }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["shot-specs", sceneId] }),
    onError: (e: Error) => setError(e.message),
  });

  const generateKeyframe = useMutation({
    mutationFn: async () => {
      if (!latestSpec) throw new Error("Save or suggest a shot spec first");
      return api.submitGeneration(sceneId, {
        generation_type: "keyframe",
        shot_spec_id: latestSpec.id,
      });
    },
    onSuccess: (res) => {
      setActiveGenId(res.generation_id);
      qc.invalidateQueries({ queryKey: ["generations", sceneId] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e: Error) => setError(e.message),
  });

  const generateVideo = useMutation({
    mutationFn: async () => {
      if (!latestSpec) throw new Error("Shot spec required");
      const ref = selectedKeyframe?.assets[0];
      if (!ref) throw new Error("Generate and complete a keyframe first");
      return api.submitGeneration(sceneId, {
        generation_type: "image_to_video",
        shot_spec_id: latestSpec.id,
        reference_asset_id: ref.id,
        duration_seconds: 4,
      });
    },
    onSuccess: (res) => {
      setActiveGenId(res.generation_id);
      qc.invalidateQueries({ queryKey: ["generations", sceneId] });
    },
    onError: (e: Error) => setError(e.message),
  });

  const review = useMutation({
    mutationFn: async (decision: "approved" | "rejected") => {
      if (!activeAsset) throw new Error("No asset to review");
      return api.reviewAsset(
        activeAsset.id,
        decision,
        decision === "rejected" ? rejectComment : undefined,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      setRejectComment("");
    },
    onError: (e: Error) => setError(e.message),
  });

  const rerun = useMutation({
    mutationFn: async () => {
      if (!activeGen) throw new Error("No generation selected");
      return api.rerunGeneration(activeGen.id);
    },
    onSuccess: (res) => {
      setActiveGenId(res.generation_id);
      qc.invalidateQueries({ queryKey: ["generations", sceneId] });
    },
    onError: (e: Error) => setError(e.message),
  });

  if (scene.isLoading) return <p className="muted">Loading scene…</p>;
  if (!scene.data) return <p className="error">Scene not found</p>;

  return (
    <div>
      <div className="muted">
        {project.data ? (
          <Link to={`/projects/${project.data.id}`}>{project.data.name}</Link>
        ) : (
          "Project"
        )}{" "}
        / Episode {scene.data.episode_no ?? "—"} / Scene {scene.data.scene_no ?? "—"}
      </div>
      <h1>{scene.data.title}</h1>

      {error && <p className="error">{error}</p>}

      <section className="panel">
        <h2>Scene brief</h2>
        <textarea value={brief} onChange={(e) => setBrief(e.target.value)} />
        <div className="row" style={{ marginTop: "0.75rem" }}>
          <button onClick={() => saveBrief.mutate()} disabled={saveBrief.isPending}>
            Save brief
          </button>
          <button
            className="primary"
            onClick={() => suggest.mutate()}
            disabled={suggest.isPending}
          >
            Generate shot spec
          </button>
        </div>
      </section>

      <section className="panel">
        <h2>Shot specification {latestSpec ? `(v${latestSpec.version})` : ""}</h2>
        <div className="grid-2">
          {(
            [
              ["location", "Location"],
              ["time_of_day", "Time of day"],
              ["action", "Action"],
              ["shot_size", "Shot size"],
              ["camera_angle", "Camera angle"],
              ["camera_motion", "Camera motion"],
              ["lighting", "Lighting"],
              ["mood", "Mood"],
            ] as const
          ).map(([key, label]) => (
            <label key={key}>
              {label}
              <input
                value={draft[key]}
                onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))}
              />
            </label>
          ))}
          <label>
            Subjects (comma-separated)
            <input
              value={draft.subjects.join(", ")}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  subjects: e.target.value
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean),
                }))
              }
            />
          </label>
          <label>
            Visual prompt
            <textarea
              value={draft.visual_prompt}
              onChange={(e) => setDraft((d) => ({ ...d, visual_prompt: e.target.value }))}
            />
          </label>
          <label>
            Motion prompt
            <textarea
              value={draft.motion_prompt}
              onChange={(e) => setDraft((d) => ({ ...d, motion_prompt: e.target.value }))}
            />
          </label>
        </div>
        <div className="row" style={{ marginTop: "0.75rem" }}>
          <button className="primary" onClick={() => saveSpec.mutate()} disabled={saveSpec.isPending}>
            Save shot spec
          </button>
        </div>
      </section>

      <section className="panel">
        <h2>Keyframe</h2>
        <div className="row">
          <button
            className="primary"
            onClick={() => generateKeyframe.mutate()}
            disabled={generateKeyframe.isPending || !latestSpec}
          >
            Generate keyframe
          </button>
        </div>
        {selectedKeyframe?.assets[0]?.url && (
          <div style={{ marginTop: "0.9rem" }}>
            <img
              className="preview"
              src={selectedKeyframe.assets[0].url}
              alt="AI-generated keyframe"
            />
            <p className="muted">AI-generated · use as reference for I2V</p>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Video generation</h2>
        <p className="muted">Workflow cinematic_i2v_v1 · duration 4 sec</p>
        <div className="row">
          <button
            className="primary"
            onClick={() => generateVideo.mutate()}
            disabled={generateVideo.isPending || !selectedKeyframe}
          >
            Generate video
          </button>
        </div>
      </section>

      {activeGen && (
        <section className="panel">
          <div className="row">
            <h2 style={{ margin: 0 }}>Generation #{activeGen.id}</h2>
            <span className={`status ${activeGen.status}`}>{activeGen.status}</span>
          </div>
          {activeAsset?.url && (
            <img
              className="preview"
              style={{ marginTop: "0.8rem" }}
              src={activeAsset.url}
              alt="AI-generated asset preview"
            />
          )}
          <div className="grid-2" style={{ marginTop: "0.9rem" }}>
            <div>
              <div className="muted">Model</div>
              <div>
                {activeGen.model_name} / {activeGen.model_version}
              </div>
            </div>
            <div>
              <div className="muted">Seed</div>
              <div>{activeGen.seed}</div>
            </div>
            <div>
              <div className="muted">Workflow</div>
              <div>
                {activeGen.workflow_version?.name} · hash{" "}
                {activeGen.workflow_version?.workflow_hash.slice(0, 10)}…
              </div>
            </div>
            <div>
              <div className="muted">Timing</div>
              <div>{activeGen.generation_ms != null ? `${activeGen.generation_ms} ms` : "—"}</div>
            </div>
            <div>
              <div className="muted">Parent</div>
              <div>{activeGen.parent_generation_id ?? "—"}</div>
            </div>
            <div>
              <div className="muted">Provider</div>
              <div>{activeGen.provider}</div>
            </div>
          </div>
          {activeGen.error_message && (
            <p className="error">
              {activeGen.error_code}: {activeGen.error_message}
            </p>
          )}
          {activeGen.status === "completed" && activeAsset && (
            <>
              <label style={{ marginTop: "0.9rem" }}>
                Reject reason
                <textarea
                  value={rejectComment}
                  onChange={(e) => setRejectComment(e.target.value)}
                  placeholder="Camera motion is too aggressive. Lighting should be slightly warmer."
                />
              </label>
              <div className="row" style={{ marginTop: "0.75rem" }}>
                <button className="danger" onClick={() => review.mutate("rejected")}>
                  Reject
                </button>
                <button className="primary" onClick={() => review.mutate("approved")}>
                  Approve
                </button>
                <button onClick={() => rerun.mutate()}>Exact re-run</button>
              </div>
            </>
          )}
        </section>
      )}

      <section className="panel">
        <h2>History</h2>
        {(generations.data || []).map((g) => (
          <button
            key={g.id}
            className="history-item"
            style={{
              width: "100%",
              textAlign: "left",
              background: "transparent",
              border: "none",
              borderBottom: "1px solid var(--line)",
              borderRadius: 0,
              padding: "0.7rem 0",
            }}
            onClick={() => setActiveGenId(g.id)}
          >
            <div>#{g.id}</div>
            <div>
              <div>
                {g.generation_type} · seed {g.seed}
                {g.parent_generation_id ? ` · child of #${g.parent_generation_id}` : ""}
              </div>
              <div className="muted">{g.prompt.slice(0, 100)}…</div>
            </div>
            <span className={`status ${g.status}`}>{g.status}</span>
          </button>
        ))}
        {(generations.data || []).length === 0 && (
          <p className="muted">No generations yet.</p>
        )}
      </section>
    </div>
  );
}
