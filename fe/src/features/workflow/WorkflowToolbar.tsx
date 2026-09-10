import { ExternalLink, Maximize2, ZoomIn, ZoomOut } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { WorkflowGraph } from "./workflowTypes";

type Props = {
  graph: WorkflowGraph | null;
  activeTab: "keyframe_v1" | "i2v_v1";
  onTabChange: (tab: "keyframe_v1" | "i2v_v1") => void;
  lockTab?: boolean;
  comfyUrl: string | null;
  onFitView: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
};

export function WorkflowToolbar({
  graph,
  activeTab,
  onTabChange,
  lockTab,
  comfyUrl,
  onFitView,
  onZoomIn,
  onZoomOut,
}: Props) {
  const hash = graph?.workflow_hash ? `${graph.workflow_hash.slice(0, 12)}…` : "—";

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-border bg-[hsl(222_27%_7%)] px-3 py-2">
      <Badge variant="outline" className="font-mono text-[10px] uppercase tracking-wide">
        Read only
      </Badge>
      {graph?.frozen && (
        <Badge variant="warning" className="text-[10px]">
          Frozen workflow snapshot
        </Badge>
      )}
      {!lockTab && (
        <div className="flex rounded-md border border-border p-0.5">
          <button
            type="button"
            className={`rounded px-2 py-1 text-xs ${
              activeTab === "keyframe_v1" ? "bg-accent text-foreground" : "text-muted-foreground"
            }`}
            onClick={() => onTabChange("keyframe_v1")}
          >
            Keyframe
          </button>
          <button
            type="button"
            className={`rounded px-2 py-1 text-xs ${
              activeTab === "i2v_v1" ? "bg-accent text-foreground" : "text-muted-foreground"
            }`}
            onClick={() => onTabChange("i2v_v1")}
          >
            Image → Video
          </button>
        </div>
      )}
      <div className="min-w-0 flex-1 text-xs text-muted-foreground">
        <span className="font-mono text-foreground/90">
          {graph?.workflow_name || "—"}
          {graph?.workflow_version ? ` · ${graph.workflow_version}` : ""}
        </span>
        {graph?.model_name ? ` · ${graph.model_name}` : ""}
        <span className="ml-2 font-mono">{hash}</span>
        {graph?.generation_id != null && (
          <span className="ml-2">Gen #{graph.generation_id}</span>
        )}
        {graph && (
          <span className="ml-2">
            {graph.node_count} nodes · {graph.edge_count} edges
          </span>
        )}
      </div>
      <div className="flex items-center gap-1">
        <Button type="button" variant="ghost" size="icon" className="h-8 w-8" onClick={onZoomOut} title="Zoom out">
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button type="button" variant="ghost" size="icon" className="h-8 w-8" onClick={onZoomIn} title="Zoom in">
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button type="button" variant="ghost" size="icon" className="h-8 w-8" onClick={onFitView} title="Fit view">
          <Maximize2 className="h-4 w-4" />
        </Button>
        {comfyUrl && (
          <Button type="button" variant="outline" size="sm" asChild>
            <a href={comfyUrl} target="_blank" rel="noreferrer">
              <ExternalLink className="h-3.5 w-3.5" />
              Open ComfyUI
            </a>
          </Button>
        )}
      </div>
    </div>
  );
}
