import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";

export function DashboardPage() {
  const metrics = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.listProjects });

  return (
    <div>
      <h1>Ops summary</h1>
      <p className="muted">
        Provenance-first AI Creation workflow — generate, review, regenerate, approve, trace.
      </p>

      {metrics.isLoading && <p className="muted">Loading metrics…</p>}
      {metrics.data && (
        <div className="metric-grid panel">
          <div className="metric">
            <div className="muted">Generation jobs</div>
            <div className="value">{metrics.data.generation_jobs}</div>
          </div>
          <div className="metric">
            <div className="muted">Approved assets</div>
            <div className="value">{metrics.data.approved_assets}</div>
          </div>
          <div className="metric">
            <div className="muted">Approval rate</div>
            <div className="value">{(metrics.data.approval_rate * 100).toFixed(0)}%</div>
          </div>
          <div className="metric">
            <div className="muted">Avg attempts / approval</div>
            <div className="value">{metrics.data.avg_attempts_per_approval}</div>
          </div>
          <div className="metric">
            <div className="muted">Avg generation ms</div>
            <div className="value">
              {metrics.data.avg_generation_ms != null
                ? Math.round(metrics.data.avg_generation_ms)
                : "—"}
            </div>
          </div>
          <div className="metric">
            <div className="muted">Failed jobs</div>
            <div className="value">{metrics.data.failed_jobs}</div>
          </div>
        </div>
      )}

      <section className="panel">
        <h2>Projects</h2>
        {projects.data?.length === 0 && (
          <p className="muted">No projects yet. Run <code>make seed</code>.</p>
        )}
        <ul>
          {projects.data?.map((p) => (
            <li key={p.id}>
              <Link to={`/projects/${p.id}`}>{p.name}</Link>
              <span className="muted"> — {p.description}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
