import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FolderSearch, Plus } from "lucide-react";
import { api } from "@/api/client";
import { CreateProjectDialog } from "@/components/projects/CreateProjectDialog";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

function CreateSceneDialog({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [episodeNo, setEpisodeNo] = useState("");
  const [sceneNo, setSceneNo] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      api.createScene(projectId, {
        title: title.trim(),
        brief: brief.trim(),
        episode_no: episodeNo ? Number(episodeNo) : null,
        scene_no: sceneNo ? Number(sceneNo) : null,
      }),
    onSuccess: async (scene) => {
      await queryClient.invalidateQueries({ queryKey: ["scenes", projectId] });
      setOpen(false);
      setTitle("");
      setBrief("");
      setEpisodeNo("");
      setSceneNo("");
      setError(null);
      navigate(`/scenes/${scene.id}`);
    },
    onError: (err: Error) => setError(err.message || "Could not create scene"),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setError("Scene title is required");
      return;
    }
    create.mutate();
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4" />
          New scene
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create scene</DialogTitle>
          <DialogDescription>
            Add a scene workspace for shot specs, references, and generation.
          </DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={submit}>
          <div className="space-y-1.5">
            <Label htmlFor="scene-title">Title</Label>
            <Input
              id="scene-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Rooftop confrontation"
              autoFocus
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="episode-no">Episode</Label>
              <Input
                id="episode-no"
                type="number"
                min={1}
                value={episodeNo}
                onChange={(e) => setEpisodeNo(e.target.value)}
                placeholder="1"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="scene-no">Scene #</Label>
              <Input
                id="scene-no"
                type="number"
                min={1}
                value={sceneNo}
                onChange={(e) => setSceneNo(e.target.value)}
                placeholder="1"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="scene-brief">Brief</Label>
            <Textarea
              id="scene-brief"
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              placeholder="What happens in this scene?"
              className="min-h-[88px]"
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create scene"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function ProjectPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const invalidId = !Number.isFinite(projectId) || projectId <= 0;

  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
    enabled: !invalidId,
    retry: false,
  });
  const scenes = useQuery({
    queryKey: ["scenes", projectId],
    queryFn: () => api.listScenes(projectId),
    enabled: !invalidId && !!project.data,
  });

  if (invalidId || project.isError || (!project.isLoading && !project.data)) {
    return (
      <div className="mx-auto max-w-dashboard">
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-card/40 px-6 py-16 text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <FolderSearch className="h-6 w-6" />
          </div>
          <h2 className="mb-2 text-lg font-semibold tracking-tight">Project not found</h2>
          <p className="mb-6 max-w-md text-sm text-muted-foreground">
            This project doesn’t exist yet, or the link is outdated. Create a new project or
            browse the projects you already have.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-2">
            <CreateProjectDialog triggerLabel="Create project" />
            <Button asChild variant="outline">
              <Link to="/projects">Browse projects</Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (project.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        breadcrumbs={
          <>
            <Link to="/">Dashboard</Link>
            <span className="mx-1.5 text-muted-foreground/60">/</span>
            <Link to="/projects">Projects</Link>
          </>
        }
        title={project.data.name}
        description={project.data.description || undefined}
        badge={<Badge variant="info">{project.data.status}</Badge>}
        actions={<CreateSceneDialog projectId={projectId} />}
      />

      <h2 className="mb-3 text-base font-semibold">Scenes</h2>
      {scenes.isLoading && <Skeleton className="h-20 w-full" />}
      {scenes.data?.length === 0 && (
        <div className="mb-3 flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-card/40 px-6 py-12 text-center">
          <p className="mb-1 text-sm font-medium">No scenes yet</p>
          <p className="mb-4 max-w-sm text-sm text-muted-foreground">
            Add a scene to start drafting shot specs and running generation.
          </p>
          <CreateSceneDialog projectId={projectId} />
        </div>
      )}
      <div className="space-y-3">
        {scenes.data?.map((s) => (
          <Link key={s.id} to={`/scenes/${s.id}`} className="block">
            <Card className="transition-colors hover:border-white/14 hover:bg-accent/30">
              <CardContent className="flex items-center justify-between gap-4 p-4">
                <div>
                  <CardTitle className="text-base">{s.title}</CardTitle>
                  <CardDescription className="mt-1">
                    Episode {s.episode_no ?? "—"} / Scene {s.scene_no ?? "—"}
                  </CardDescription>
                </div>
                <Badge variant="outline">{s.status}</Badge>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
