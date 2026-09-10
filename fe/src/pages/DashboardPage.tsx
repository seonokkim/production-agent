import { Activity, CheckCircle2, Clock3, FileText, FolderOpen, Layers, Percent, TimerReset, XCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { CreateProjectDialog } from "@/components/projects/CreateProjectDialog";
import { EmptyProjectsState } from "@/components/projects/EmptyProjectsState";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDurationMs, formatRelativeTime } from "@/lib/utils";

const metricMeta = [
  { key: "generation_jobs" as const, label: "Generation jobs", icon: Layers },
  { key: "approved_assets" as const, label: "Approved assets", icon: CheckCircle2 },
  { key: "approval_rate" as const, label: "Approval rate", icon: Percent, format: (v: number) => `${(v * 100).toFixed(0)}%` },
  { key: "avg_attempts_per_approval" as const, label: "Avg attempts", icon: Activity },
  { key: "avg_generation_ms" as const, label: "Avg gen time", icon: Clock3, format: (v: number | null) => formatDurationMs(v) },
  { key: "failed_jobs" as const, label: "Failed jobs", icon: XCircle },
];

const opsMeta = [
  { key: "total_assets" as const, label: "Total assets", icon: FolderOpen },
  { key: "documents" as const, label: "Documents", icon: FileText },
  { key: "pending_ingestion" as const, label: "Pending ingestion", icon: TimerReset },
  { key: "failed_ingestion" as const, label: "Failed ingestion", icon: XCircle },
];

export function DashboardPage() {
  const metrics = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.listProjects });
  const firstProject = projects.data?.[0];

  return (
    <div className="mx-auto max-w-dashboard">
      <PageHeader
        title="Dashboard"
        description="Production workflow health and recent activity."
        actions={<CreateProjectDialog />}
      />

      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {metrics.isLoading &&
          Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-[104px] rounded-lg" />
          ))}
        {metrics.data &&
          metricMeta.map((m) => {
            const Icon = m.icon;
            const raw = metrics.data[m.key];
            const value =
              "format" in m && m.format
                ? m.format(raw as never)
                : String(raw ?? "—");
            return (
              <Card key={m.key} className="transition-colors hover:border-white/14">
                <CardHeader className="flex-row items-center justify-between space-y-0 pb-1">
                  <CardDescription className="text-xs uppercase tracking-wide">
                    {m.label}
                  </CardDescription>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-[32px] font-semibold leading-none tracking-tight">
                    {value}
                  </div>
                </CardContent>
              </Card>
            );
          })}
      </div>

      <section className="mb-6">
        <h2 className="mb-3 text-base font-semibold">Asset Operations</h2>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {metrics.isLoading &&
            Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-[88px] rounded-lg" />
            ))}
          {metrics.data &&
            opsMeta.map((m) => {
              const Icon = m.icon;
              const value = String(metrics.data[m.key] ?? 0);
              return (
                <Card key={m.key} className="transition-colors hover:border-white/14">
                  <CardHeader className="flex-row items-center justify-between space-y-0 pb-1">
                    <CardDescription className="text-xs uppercase tracking-wide">
                      {m.label}
                    </CardDescription>
                    <Icon className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-semibold tracking-tight">{value}</div>
                  </CardContent>
                </Card>
              );
            })}
        </div>
        {metrics.data?.last_airflow_run_status && (
          <p className="mt-2 text-xs text-muted-foreground">
            Last batch run:{" "}
            <Badge variant="outline">{metrics.data.last_airflow_run_status}</Badge>
            {metrics.data.last_airflow_run_at
              ? ` · ${formatRelativeTime(metrics.data.last_airflow_run_at)}`
              : null}
            {typeof metrics.data.assets_indexed === "number"
              ? ` · ${metrics.data.assets_indexed} indexed`
              : null}
          </p>
        )}
      </section>

      <section className="mb-6">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold">Projects</h2>
          {!!projects.data?.length && (
            <Button asChild variant="ghost" size="sm">
              <Link to="/projects">View all</Link>
            </Button>
          )}
        </div>
        {projects.isLoading && (
          <div className="space-y-3">
            <Skeleton className="h-24 rounded-lg" />
          </div>
        )}
        {projects.data?.length === 0 && <EmptyProjectsState />}
        <div className="space-y-3">
          {projects.data?.slice(0, 5).map((p) => (
            <Link key={p.id} to={`/projects/${p.id}`} className="block">
              <Card className="transition-colors hover:border-white/14 hover:bg-accent/30">
                <CardContent className="flex items-start justify-between gap-4 p-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <CardTitle>{p.name}</CardTitle>
                      <Badge variant="info">{p.status}</Badge>
                    </div>
                    <CardDescription className="mt-1">
                      {p.description || "No description"}
                    </CardDescription>
                  </div>
                  <span className="text-muted-foreground">→</span>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-base font-semibold">Recent activity</h2>
        {metrics.data && metrics.data.generation_jobs === 0 ? (
          <Card className="p-8 text-center">
            <p className="mb-1 text-sm font-medium">No generations yet</p>
            <p className="mb-4 text-sm text-muted-foreground">
              {firstProject
                ? "Open a project, create a scene, and run your first keyframe workflow."
                : "Create a project first, then add a scene to start generating."}
            </p>
            {firstProject ? (
              <Button asChild>
                <Link to={`/projects/${firstProject.id}`}>Open {firstProject.name}</Link>
              </Button>
            ) : (
              <CreateProjectDialog triggerLabel="Create project" />
            )}
          </Card>
        ) : (
          <Card className="p-4">
            <p className="text-sm text-muted-foreground">
              {metrics.data?.generation_jobs ?? "—"} generation jobs tracked ·{" "}
              {metrics.data?.approved_assets ?? "—"} approved ·{" "}
              {metrics.data?.failed_jobs ?? "—"} failed
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              Open a scene workspace to inspect lineage, provenance, and previews.
            </p>
          </Card>
        )}
      </section>
    </div>
  );
}
