import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "@/api/client";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { WorkflowGraphView } from "./WorkflowGraph";
import type { WorkflowViewerMode } from "./workflowTypes";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: WorkflowViewerMode | null;
};

export function WorkflowViewerDialog({ open, onOpenChange, mode }: Props) {
  const [tab, setTab] = useState<"keyframe_v1" | "i2v_v1">("keyframe_v1");

  useEffect(() => {
    if (!mode) return;
    if (mode.kind === "active") setTab(mode.workflowName);
  }, [mode]);

  const frozen = mode?.kind === "generation";

  const graphQuery = useQuery({
    queryKey: ["workflow-graph", mode],
    enabled: open && !!mode,
    queryFn: async () => {
      if (!mode) throw new Error("No mode");
      if (mode.kind === "generation") {
        return api.getGenerationWorkflowGraph(mode.generationId);
      }
      return api.getWorkflowGraphByName(mode.workflowName);
    },
  });

  // When switching tabs in active mode, refetch by name.
  const activeGraphQuery = useQuery({
    queryKey: ["workflow-graph-active", tab],
    enabled: open && mode?.kind === "active",
    queryFn: () => api.getWorkflowGraphByName(tab),
  });

  const comfyQuery = useQuery({
    queryKey: ["comfyui-info"],
    enabled: open,
    queryFn: () => api.getComfyuiInfo(),
    staleTime: 60_000,
  });

  const graph =
    mode?.kind === "generation" ? graphQuery.data : activeGraphQuery.data;
  const loading =
    mode?.kind === "generation" ? graphQuery.isLoading : activeGraphQuery.isLoading;
  const error =
    mode?.kind === "generation"
      ? graphQuery.error
        ? String(graphQuery.error)
        : null
      : activeGraphQuery.error
        ? String(activeGraphQuery.error)
        : null;

  // Infer tab lock label from frozen graph type
  useEffect(() => {
    if (mode?.kind !== "generation" || !graphQuery.data) return;
    const t = graphQuery.data.workflow_type;
    const name = graphQuery.data.workflow_name;
    if (name === "i2v_v1" || t === "image_to_video") setTab("i2v_v1");
    else setTab("keyframe_v1");
  }, [mode, graphQuery.data]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[85vh] w-[90vw] max-w-[90vw] flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="shrink-0 border-b border-border px-5 py-3 pr-12">
          <DialogTitle>Workflow graph</DialogTitle>
          <DialogDescription>
            {frozen
              ? "Frozen snapshot from this generation job — inspection only."
              : "Active version-controlled ComfyUI API workflow — inspection only."}
          </DialogDescription>
        </DialogHeader>
        <div className="min-h-0 flex-1 overflow-hidden">
          <WorkflowGraphView
            graph={graph ?? null}
            loading={loading}
            error={error}
            activeTab={tab}
            onTabChange={setTab}
            lockTab={frozen}
            comfyUrl={comfyQuery.data?.comfyui_url ?? null}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
