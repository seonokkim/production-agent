import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";

export function ProjectPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
    enabled: Number.isFinite(projectId),
  });
  const scenes = useQuery({
    queryKey: ["scenes", projectId],
    queryFn: () => api.listScenes(projectId),
    enabled: Number.isFinite(projectId),
  });

  if (project.isLoading) return <p className="muted">Loading project…</p>;
  if (!project.data) return <p className="error">Project not found</p>;

  return (
    <div>
      <h1>{project.data.name}</h1>
      <p className="muted">{project.data.description}</p>
      <section className="panel">
        <h2>Scenes</h2>
        <ul>
          {scenes.data?.map((s) => (
            <li key={s.id}>
              <Link to={`/scenes/${s.id}`}>
                Episode {s.episode_no ?? "—"} / Scene {s.scene_no ?? "—"} — {s.title}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
