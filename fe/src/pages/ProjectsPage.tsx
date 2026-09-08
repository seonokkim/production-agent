import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { CreateProjectDialog } from "@/components/projects/CreateProjectDialog";
import { EmptyProjectsState } from "@/components/projects/EmptyProjectsState";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function ProjectsPage() {
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.listProjects });

  return (
    <div className="mx-auto max-w-dashboard">
      <PageHeader
        title="Projects"
        description="Production workspaces for scenes, references, and generation lineage."
        actions={<CreateProjectDialog />}
      />

      {projects.isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
        </div>
      )}

      {projects.isError && (
        <EmptyProjectsState
          title="Couldn’t load projects"
          description="Check that the backend is running, then create a project to get started."
        />
      )}

      {projects.data?.length === 0 && <EmptyProjectsState />}

      {!!projects.data?.length && (
        <div className="space-y-3">
          {projects.data.map((p) => (
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
      )}
    </div>
  );
}
