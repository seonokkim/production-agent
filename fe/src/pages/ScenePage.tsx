import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Clock3,
  Fingerprint,
  Image as ImageIcon,
  Loader2,
  Search,
  Sparkles,
  Video,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/api/client";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { cn, formatDurationMs, formatRelativeTime } from "@/lib/utils";
import type { Generation, ReferenceSearchHit, ShotSpec } from "@/types";

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

const shotSizeOptions = ["wide", "medium wide", "medium", "close-up", "extreme close-up"];
const cameraAngleOptions = ["eye level", "low", "high", "overhead", "dutch"];

function statusVariant(status: string): "success" | "warning" | "danger" | "outline" | "info" {
  if (status === "completed" || status === "approved") return "success";
  if (status === "queued" || status === "running") return "warning";
  if (status === "failed" || status === "rejected") return "danger";
  return "outline";
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

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
  const [rejectOpen, setRejectOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [activeGenId, setActiveGenId] = useState<number | null>(null);
  const [genTab, setGenTab] = useState<"keyframe" | "video">("keyframe");
  const [retrievalEventId, setRetrievalEventId] = useState<number | null>(null);
  const [searchHits, setSearchHits] = useState<ReferenceSearchHit[]>([]);
  const [selectedEmbeddingId, setSelectedEmbeddingId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

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
    () => (generations.data || []).filter((g) => g.generation_type === "image_to_video"),
    [generations.data],
  );
  const activeGen =
    (generations.data || []).find((g) => g.id === activeGenId) ||
    videos[0] ||
    selectedKeyframe ||
    null;
  const activeAsset = activeGen?.assets[0];
  const selectedHit = searchHits.find((h) => h.asset_embedding_id === selectedEmbeddingId);

  const saveBrief = useMutation({
    mutationFn: () => api.updateScene(sceneId, { brief }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scene", sceneId] });
      toast.success("Scene brief saved");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const suggest = useMutation({
    mutationFn: async () => {
      await api.updateScene(sceneId, { brief });
      return api.suggestShotSpec(sceneId);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["shot-specs", sceneId] });
      toast.success("Shot specification suggested");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const saveSpec = useMutation({
    mutationFn: () => api.saveShotSpec(sceneId, { ...draft, subjects: draft.subjects }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["shot-specs", sceneId] });
      toast.success("Shot specification saved");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const referenceSearch = useMutation({
    mutationFn: async () => {
      if (!latestSpec) throw new Error("Save or suggest a shot spec first");
      return api.referenceSearch(sceneId, {
        shot_spec_id: latestSpec.id,
        query_text: searchQuery || undefined,
        top_k: 3,
      });
    },
    onSuccess: (res) => {
      setRetrievalEventId(res.retrieval_event_id);
      setSearchHits(res.results);
      setSelectedEmbeddingId(null);
      setSearchQuery(res.query_text);
      toast.success("Reference search complete");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const selectReference = useMutation({
    mutationFn: async (embeddingId: number) => {
      if (!retrievalEventId) throw new Error("Run reference search first");
      await api.selectReference(retrievalEventId, embeddingId);
      return embeddingId;
    },
    onSuccess: (embeddingId) => {
      setSelectedEmbeddingId(embeddingId);
      toast.success("Reference selected");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const generateKeyframe = useMutation({
    mutationFn: async () => {
      if (!latestSpec) throw new Error("Save or suggest a shot spec first");
      return api.submitGeneration(sceneId, {
        generation_type: "keyframe",
        shot_spec_id: latestSpec.id,
        reference_asset_embedding_id: selectedEmbeddingId ?? undefined,
        retrieval_event_id: retrievalEventId ?? undefined,
      });
    },
    onSuccess: (res) => {
      setActiveGenId(res.generation_id);
      setGenTab("keyframe");
      qc.invalidateQueries({ queryKey: ["generations", sceneId] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Generation queued");
    },
    onError: (e: Error) => toast.error(e.message),
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
        reference_asset_embedding_id: selectedEmbeddingId ?? undefined,
        retrieval_event_id: retrievalEventId ?? undefined,
        duration_seconds: 4,
      });
    },
    onSuccess: (res) => {
      setActiveGenId(res.generation_id);
      setGenTab("video");
      qc.invalidateQueries({ queryKey: ["generations", sceneId] });
      toast.success("Generation queued");
    },
    onError: (e: Error) => toast.error(e.message),
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
    onSuccess: (_data, decision) => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["generations", sceneId] });
      qc.invalidateQueries({ queryKey: ["assets"] });
      setRejectComment("");
      setRejectOpen(false);
      toast.success(decision === "approved" ? "Asset approved" : "Asset rejected");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const rerun = useMutation({
    mutationFn: async () => {
      if (!activeGen) throw new Error("No generation selected");
      return api.rerunGeneration(activeGen.id);
    },
    onSuccess: (res) => {
      setActiveGenId(res.generation_id);
      qc.invalidateQueries({ queryKey: ["generations", sceneId] });
      toast.success("Exact rerun created");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (scene.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-[480px] w-full" />
      </div>
    );
  }
  if (!scene.data) {
    return <p className="text-sm text-destructive">Scene not found</p>;
  }

  return (
    <div>
      <PageHeader
        breadcrumbs={
          <span>
            {project.data ? (
              <Link to={`/projects/${project.data.id}`} className="hover:text-foreground">
                {project.data.name}
              </Link>
            ) : (
              "Project"
            )}{" "}
            / Episode {scene.data.episode_no ?? "—"} / Scene {scene.data.scene_no ?? "—"}
          </span>
        }
        title={scene.data.title}
        badge={<Badge variant="outline">{scene.data.status || "Draft"}</Badge>}
        actions={
          <>
            <Button variant="secondary" onClick={() => saveBrief.mutate()} disabled={saveBrief.isPending}>
              Save
            </Button>
            <Button
              onClick={() => (genTab === "video" ? generateVideo.mutate() : generateKeyframe.mutate())}
              disabled={
                genTab === "video"
                  ? generateVideo.isPending || !selectedKeyframe
                  : generateKeyframe.isPending || !latestSpec
              }
            >
              <Sparkles className="h-4 w-4" />
              Generate
            </Button>
          </>
        }
      />

      <div className="grid gap-6 xl:grid-cols-12">
        {/* LEFT — Planning */}
        <div className="space-y-4 xl:col-span-5">
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>Scene brief</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea
                className="min-h-[180px] text-sm leading-relaxed"
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
              />
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  onClick={() => saveBrief.mutate()}
                  disabled={saveBrief.isPending}
                >
                  Save
                </Button>
                <Button onClick={() => suggest.mutate()} disabled={suggest.isPending}>
                  <Sparkles className="h-4 w-4" />
                  Suggest shot spec
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>
                Shot specification {latestSpec ? `(v${latestSpec.version})` : ""}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Scene
                </h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Location">
                    <Input
                      value={draft.location}
                      onChange={(e) => setDraft((d) => ({ ...d, location: e.target.value }))}
                    />
                  </Field>
                  <Field label="Time of day">
                    <Input
                      value={draft.time_of_day}
                      onChange={(e) => setDraft((d) => ({ ...d, time_of_day: e.target.value }))}
                    />
                  </Field>
                  <Field label="Mood">
                    <Input
                      value={draft.mood}
                      onChange={(e) => setDraft((d) => ({ ...d, mood: e.target.value }))}
                    />
                  </Field>
                </div>
                {(draft.mood || draft.location) && (
                  <div className="flex flex-wrap gap-1.5">
                    {draft.mood && <Badge>{draft.mood}</Badge>}
                    {draft.location && <Badge variant="outline">{draft.location}</Badge>}
                  </div>
                )}
              </section>

              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Subject & action
                </h3>
                <Field label="Subjects (comma-separated)">
                  <Input
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
                </Field>
                <Field label="Action">
                  <Input
                    value={draft.action}
                    onChange={(e) => setDraft((d) => ({ ...d, action: e.target.value }))}
                  />
                </Field>
                {draft.subjects.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {draft.subjects.map((s) => (
                      <Badge key={s} variant="outline">
                        {s}
                      </Badge>
                    ))}
                  </div>
                )}
              </section>

              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Camera
                </h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Shot size">
                    <Input
                      list="shot-size-options"
                      value={draft.shot_size}
                      onChange={(e) => setDraft((d) => ({ ...d, shot_size: e.target.value }))}
                    />
                    <datalist id="shot-size-options">
                      {shotSizeOptions.map((o) => (
                        <option key={o} value={o} />
                      ))}
                    </datalist>
                  </Field>
                  <Field label="Camera angle">
                    <Input
                      list="camera-angle-options"
                      value={draft.camera_angle}
                      onChange={(e) => setDraft((d) => ({ ...d, camera_angle: e.target.value }))}
                    />
                    <datalist id="camera-angle-options">
                      {cameraAngleOptions.map((o) => (
                        <option key={o} value={o} />
                      ))}
                    </datalist>
                  </Field>
                  <Field label="Camera motion">
                    <Input
                      value={draft.camera_motion}
                      onChange={(e) => setDraft((d) => ({ ...d, camera_motion: e.target.value }))}
                    />
                  </Field>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {draft.shot_size && <Badge variant="outline">{draft.shot_size}</Badge>}
                  {draft.camera_motion && <Badge variant="outline">{draft.camera_motion}</Badge>}
                </div>
              </section>

              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Look
                </h3>
                <Field label="Lighting">
                  <Input
                    value={draft.lighting}
                    onChange={(e) => setDraft((d) => ({ ...d, lighting: e.target.value }))}
                  />
                </Field>
                {draft.lighting && <Badge variant="outline">{draft.lighting}</Badge>}
              </section>

              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Prompts
                </h3>
                <Field label="Visual prompt">
                  <Textarea
                    className="min-h-[88px]"
                    value={draft.visual_prompt}
                    onChange={(e) => setDraft((d) => ({ ...d, visual_prompt: e.target.value }))}
                  />
                </Field>
                <Field label="Motion prompt">
                  <Textarea
                    className="min-h-[88px]"
                    value={draft.motion_prompt}
                    onChange={(e) => setDraft((d) => ({ ...d, motion_prompt: e.target.value }))}
                  />
                </Field>
              </section>

              <Button onClick={() => saveSpec.mutate()} disabled={saveSpec.isPending}>
                Save shot spec
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="h-4 w-4" />
                Reference search
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-muted-foreground">
                Search previously approved clips. Human selection is required before the reference
                is attached to provenance.
              </p>
              <Field label="Query">
                <Textarea
                  className="min-h-[88px]"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="A slow rear tracking shot in a dark industrial interior…"
                />
              </Field>
              <Button
                variant="secondary"
                onClick={() => referenceSearch.mutate()}
                disabled={referenceSearch.isPending || !latestSpec}
              >
                Search approved assets
              </Button>

              {searchHits.length === 0 && !referenceSearch.isPending && (
                <p className="text-xs text-muted-foreground">No approved references found yet.</p>
              )}

              <div className="grid gap-3 sm:grid-cols-3">
                {searchHits.map((hit) => {
                  const selected = selectedEmbeddingId === hit.asset_embedding_id;
                  return (
                    <div
                      key={hit.asset_embedding_id}
                      className={cn(
                        "rounded-md border border-border bg-background/40 p-2",
                        selected && "ring-2 ring-primary",
                      )}
                    >
                      <div className="mb-2 aspect-video overflow-hidden rounded bg-black/40">
                        {hit.thumbnail_url ? (
                          <img
                            src={hit.thumbnail_url}
                            alt="Approved reference"
                            className="h-full w-full object-contain"
                          />
                        ) : (
                          <div className="flex h-full items-center justify-center text-muted-foreground">
                            <Video className="h-5 w-5" />
                          </div>
                        )}
                      </div>
                      <div className="mb-1 flex items-center justify-between gap-1">
                        <Badge variant="info">{hit.score.toFixed(2)}</Badge>
                        {selected && <Check className="h-3.5 w-3.5 text-primary" />}
                      </div>
                      <div className="mb-2 line-clamp-2 text-xs text-muted-foreground">
                        {hit.camera_motion} · {hit.lighting} · {hit.mood}
                      </div>
                      <Button
                        size="sm"
                        variant={selected ? "default" : "outline"}
                        className="w-full"
                        onClick={() => selectReference.mutate(hit.asset_embedding_id)}
                        disabled={selectReference.isPending}
                      >
                        {selected ? "Selected" : "Use"}
                      </Button>
                    </div>
                  );
                })}
              </div>
              {selectedHit && (
                <p className="text-xs text-muted-foreground">
                  Selected reference asset #{selectedHit.asset_id} · event #{retrievalEventId}
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* RIGHT — Preview & Generation */}
        <div className="space-y-4 xl:col-span-7">
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>Preview</CardTitle>
              {activeGen && (
                <Badge variant={statusVariant(activeGen.status)}>{activeGen.status}</Badge>
              )}
            </CardHeader>
            <CardContent>
              <div className="flex aspect-video items-center justify-center overflow-hidden rounded-md border border-border bg-[linear-gradient(45deg,#111_25%,transparent_25%),linear-gradient(-45deg,#111_25%,transparent_25%),linear-gradient(45deg,transparent_75%,#111_75%),linear-gradient(-45deg,transparent_75%,#111_75%)] bg-[length:16px_16px] bg-[position:0_0,0_8px,8px_-8px,-8px_0] bg-black/50">
                {activeAsset?.url ? (
                  activeAsset.mime_type.startsWith("video/") ? (
                    <video
                      src={activeAsset.url}
                      controls
                      className="h-full w-full object-contain"
                    />
                  ) : (
                    <img
                      src={activeAsset.url}
                      alt="Generated asset"
                      className="h-full w-full object-contain"
                    />
                  )
                ) : (
                  <div className="px-6 text-center">
                    <ImageIcon className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
                    <p className="text-sm font-medium">No preview yet</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Generate a keyframe to start visual exploration.
                    </p>
                  </div>
                )}
              </div>

              {activeGen && (
                <div className="mt-4 space-y-3">
                  {(activeGen.status === "queued" || activeGen.status === "running") && (
                    <div className="flex items-center gap-2 rounded-md border border-border bg-secondary/40 px-3 py-2 text-sm">
                      {activeGen.status === "queued" ? (
                        <Clock3 className="h-4 w-4 text-warning" />
                      ) : (
                        <Loader2 className="h-4 w-4 animate-spin text-warning" />
                      )}
                      <span>
                        {activeGen.status === "queued"
                          ? "Queued"
                          : `Generating ${activeGen.generation_type}…`}
                      </span>
                    </div>
                  )}
                  {activeGen.status === "completed" && (
                    <div className="flex items-center gap-2 text-sm text-success">
                      <CheckCircle2 className="h-4 w-4" />
                      Completed in {formatDurationMs(activeGen.generation_ms)}
                    </div>
                  )}
                  {activeGen.status === "failed" && (
                    <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm">
                      <div className="mb-1 flex items-center gap-2 font-medium text-destructive">
                        <AlertCircle className="h-4 w-4" />
                        Generation failed
                      </div>
                      <p className="text-muted-foreground">
                        {activeGen.error_code}: {activeGen.error_message}
                      </p>
                      <p className="mt-2 text-xs text-muted-foreground">
                        Existing approved assets are unchanged.
                      </p>
                    </div>
                  )}

                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Fingerprint className="h-3.5 w-3.5" />
                    Provenance
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <Meta label="Workflow" value={activeGen.workflow_version?.name || "—"} mono />
                    <Meta label="Model" value={`${activeGen.model_name} / ${activeGen.model_version}`} />
                    <Meta label="Seed" value={String(activeGen.seed)} mono />
                    <Meta
                      label="Reference"
                      value={
                        activeGen.reference_asset_id
                          ? `#${activeGen.reference_asset_id}`
                          : "—"
                      }
                      mono
                    />
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => setDetailOpen(true)}>
                    View full provenance
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Generation</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs
                value={genTab}
                onValueChange={(v) => setGenTab(v as "keyframe" | "video")}
              >
                <TabsList>
                  <TabsTrigger value="keyframe">Keyframe</TabsTrigger>
                  <TabsTrigger value="video">Video</TabsTrigger>
                </TabsList>
                <TabsContent value="keyframe" className="space-y-3">
                  <dl className="grid gap-2 text-sm sm:grid-cols-2">
                    <Meta label="Workflow" value="keyframe_v1" mono />
                    <Meta label="Seed" value="Random" />
                    <Meta label="Resolution" value="1280 × 720" mono />
                  </dl>
                  <Button
                    onClick={() => generateKeyframe.mutate()}
                    disabled={generateKeyframe.isPending || !latestSpec}
                  >
                    <ImageIcon className="h-4 w-4" />
                    Generate keyframe
                  </Button>
                </TabsContent>
                <TabsContent value="video" className="space-y-3">
                  <div className="flex items-center gap-3 rounded-md border border-border p-2">
                    <div className="h-14 w-24 overflow-hidden rounded bg-black/40">
                      {selectedKeyframe?.assets[0]?.url ? (
                        <img
                          src={selectedKeyframe.assets[0].url}
                          alt="Reference keyframe"
                          className="h-full w-full object-contain"
                        />
                      ) : (
                        <div className="flex h-full items-center justify-center text-muted-foreground">
                          <ImageIcon className="h-4 w-4" />
                        </div>
                      )}
                    </div>
                    <div className="text-sm">
                      <div className="font-medium">Reference keyframe</div>
                      <div className="text-xs text-muted-foreground">
                        {selectedKeyframe
                          ? `#${selectedKeyframe.id}`
                          : "Generate a keyframe first"}
                      </div>
                    </div>
                  </div>
                  <dl className="grid gap-2 text-sm sm:grid-cols-2">
                    <Meta label="Workflow" value="i2v_v1" mono />
                    <Meta label="Duration" value="4 sec" />
                  </dl>
                  <Button
                    onClick={() => generateVideo.mutate()}
                    disabled={generateVideo.isPending || !selectedKeyframe}
                  >
                    <Video className="h-4 w-4" />
                    Generate video
                  </Button>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {activeGen?.status === "completed" && activeAsset && (
            <Card>
              <CardHeader>
                <CardTitle>Review</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                <Button variant="success" onClick={() => review.mutate("approved")}>
                  Approve
                </Button>
                <Button variant="destructive" onClick={() => setRejectOpen(true)}>
                  Reject
                </Button>
                <Button
                  variant="outline"
                  title="Same frozen configuration → new job"
                  onClick={() => rerun.mutate()}
                  disabled={rerun.isPending}
                >
                  Exact rerun
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* BOTTOM — History */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Generation history</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(generations.data || []).length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No generation history.
            </p>
          )}
          {(generations.data || []).map((g) => (
            <button
              key={g.id}
              type="button"
              onClick={() => {
                setActiveGenId(g.id);
                setDetailOpen(true);
              }}
              className={cn(
                "flex w-full items-start gap-3 rounded-md border border-transparent px-3 py-3 text-left transition-colors hover:border-border hover:bg-accent/40",
                activeGenId === g.id && "border-border bg-accent/30",
              )}
            >
              <div className="h-14 w-20 shrink-0 overflow-hidden rounded bg-black/40">
                {g.assets[0]?.url ? (
                  <img
                    src={g.assets[0].url}
                    alt=""
                    className="h-full w-full object-contain"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-muted-foreground">
                    <ImageIcon className="h-4 w-4" />
                  </div>
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-medium">v{g.id}</span>
                  <Badge variant={statusVariant(g.status)}>{g.status}</Badge>
                  <span className="text-xs text-muted-foreground">{g.generation_type}</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {g.model_name} · {formatDurationMs(g.generation_ms)} ·{" "}
                  {formatRelativeTime(g.completed_at || g.queued_at)}
                  {g.parent_generation_id ? ` · parent: v${g.parent_generation_id}` : ""}
                </div>
              </div>
            </button>
          ))}
        </CardContent>
      </Card>

      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject asset</DialogTitle>
            <DialogDescription>What should be improved?</DialogDescription>
          </DialogHeader>
          <Textarea
            className="min-h-[120px]"
            value={rejectComment}
            onChange={(e) => setRejectComment(e.target.value)}
            placeholder="Camera motion is too aggressive. Lighting should be slightly warmer."
          />
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setRejectOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => review.mutate("rejected")}
              disabled={review.isPending}
            >
              Reject & continue
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Sheet open={detailOpen} onOpenChange={setDetailOpen}>
        <SheetContent>
          {activeGen ? (
            <div className="space-y-5">
              <div>
                <h2 className="flex items-center gap-2 text-lg font-semibold">
                  <Fingerprint className="h-4 w-4" />
                  Generation #{activeGen.id}
                </h2>
                <p className="text-sm text-muted-foreground">
                  {activeGen.generation_type} · {activeGen.status}
                </p>
              </div>

              <section className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Provenance
                </h3>
                <dl className="space-y-2 text-sm">
                  <Row k="Provider" v={activeGen.provider} />
                  <Row k="Model" v={`${activeGen.model_name} / ${activeGen.model_version}`} />
                  <Row
                    k="Workflow"
                    v={`${activeGen.workflow_version?.name || "—"} · ${activeGen.workflow_version?.version || ""}`}
                    mono
                  />
                  <Row
                    k="Workflow hash"
                    v={
                      activeGen.workflow_version?.workflow_hash
                        ? `${activeGen.workflow_version.workflow_hash.slice(0, 12)}…`
                        : "—"
                    }
                    mono
                  />
                  <Row k="Seed" v={String(activeGen.seed)} mono />
                  <Row
                    k="Reference"
                    v={
                      activeGen.reference_asset_id
                        ? `#${activeGen.reference_asset_id}`
                        : "—"
                    }
                    mono
                  />
                  <Row
                    k="Retrieval event"
                    v={
                      activeGen.retrieval_event_id
                        ? `#${activeGen.retrieval_event_id}`
                        : "—"
                    }
                    mono
                  />
                  <Row k="Parent" v={activeGen.parent_generation_id ? `#${activeGen.parent_generation_id}` : "—"} mono />
                  <Row k="Generation time" v={formatDurationMs(activeGen.generation_ms)} />
                  <Row k="Created" v={new Date(activeGen.queued_at).toLocaleString()} />
                </dl>
              </section>

              <section className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Prompt
                </h3>
                <p className="rounded-md border border-border bg-background/50 p-3 text-xs leading-relaxed text-muted-foreground">
                  {activeGen.prompt}
                </p>
              </section>

              {activeGen.error_message && (
                <section className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm">
                  <div className="font-medium text-destructive">Error</div>
                  <p className="text-muted-foreground">
                    {activeGen.error_code}: {activeGen.error_message}
                  </p>
                </section>
              )}

              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  onClick={() => rerun.mutate()}
                  disabled={rerun.isPending}
                >
                  Exact rerun
                </Button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Select a generation.</p>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function Meta({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={cn("text-sm", mono && "font-mono")}>{value}</dd>
    </div>
  );
}

function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className={cn("text-right", mono && "font-mono text-xs")}>{v}</dd>
    </div>
  );
}
