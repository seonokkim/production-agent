import { Clapperboard } from "lucide-react";
import { CreateProjectDialog } from "./CreateProjectDialog";

type Props = {
  title?: string;
  description?: string;
};

export function EmptyProjectsState({
  title = "No projects yet",
  description = "Create your first project to start writing scenes, shot specs, and generations.",
}: Props) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-card/40 px-6 py-16 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/15 text-primary">
        <Clapperboard className="h-6 w-6" />
      </div>
      <h2 className="mb-2 text-lg font-semibold tracking-tight">{title}</h2>
      <p className="mb-6 max-w-md text-sm text-muted-foreground">{description}</p>
      <CreateProjectDialog triggerLabel="Create project" triggerSize="lg" />
    </div>
  );
}
