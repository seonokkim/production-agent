import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type NodeTypes,
} from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
import "@xyflow/react/dist/style.css";
import { Skeleton } from "@/components/ui/skeleton";
import { WorkflowNode } from "./WorkflowNode";
import { WorkflowToolbar } from "./WorkflowToolbar";
import { layoutWorkflowGraph } from "./workflowLayout";
import type { WorkflowGraph } from "./workflowTypes";

const nodeTypes: NodeTypes = {
  workflow: WorkflowNode as unknown as NodeTypes[string],
};

type Props = {
  graph: WorkflowGraph | null;
  loading?: boolean;
  error?: string | null;
  activeTab: "keyframe_v1" | "i2v_v1";
  onTabChange: (tab: "keyframe_v1" | "i2v_v1") => void;
  lockTab?: boolean;
  comfyUrl: string | null;
};

function GraphCanvas({
  graph,
  loading,
  error,
  activeTab,
  onTabChange,
  lockTab,
  comfyUrl,
}: Props) {
  const { fitView, zoomIn, zoomOut } = useReactFlow();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { nodes, edges } = useMemo(() => {
    if (!graph) return { nodes: [], edges: [] };
    return layoutWorkflowGraph(graph);
  }, [graph]);

  useEffect(() => {
    if (!graph) return;
    const t = window.setTimeout(() => fitView({ padding: 0.18, duration: 200 }), 50);
    return () => window.clearTimeout(t);
  }, [graph, fitView]);

  return (
    <div className="flex h-full min-h-[480px] flex-col">
      <WorkflowToolbar
        graph={graph}
        activeTab={activeTab}
        onTabChange={onTabChange}
        lockTab={lockTab}
        comfyUrl={comfyUrl}
        onFitView={() => fitView({ padding: 0.18, duration: 200 })}
        onZoomIn={() => zoomIn({ duration: 150 })}
        onZoomOut={() => zoomOut({ duration: 150 })}
      />
      <div className="relative min-h-0 flex-1 bg-[hsl(222_30%_4%)]" style={{ height: "100%" }}>
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/40">
            <Skeleton className="h-24 w-64" />
          </div>
        )}
        {error && !loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center p-6 text-sm text-destructive">
            {error}
          </div>
        )}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          panOnScroll
          zoomOnScroll
          fitView
          minZoom={0.2}
          maxZoom={1.6}
          proOptions={{ hideAttribution: true }}
          onSelectionChange={({ nodes: sel }) => setSelectedId(sel[0]?.id ?? null)}
          defaultEdgeOptions={{ type: "smoothstep" }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={18}
            size={1}
            color="hsl(222 14% 18%)"
          />
          <Controls
            showInteractive={false}
            className="!border-border !bg-card !shadow-md [&>button]:!border-border [&>button]:!bg-card [&>button]:!fill-foreground"
          />
          <MiniMap
            pannable
            zoomable
            className="!border-border !bg-[hsl(222_27%_7%)]"
            nodeColor={() => "hsl(247 50% 40%)"}
            maskColor="rgba(0,0,0,0.55)"
          />
        </ReactFlow>
        {selectedId && graph && (
          <aside className="absolute bottom-3 left-3 max-w-sm rounded-md border border-border bg-card/95 p-3 text-xs shadow-lg backdrop-blur">
            {(() => {
              const n = graph.nodes.find((x) => x.id === selectedId);
              if (!n) return null;
              return (
                <>
                  <div className="font-medium">{n.label}</div>
                  <div className="font-mono text-[10px] text-muted-foreground">{n.class_type}</div>
                  <div className="mt-2 max-h-40 overflow-auto font-mono text-[10px] text-muted-foreground">
                    <pre>{JSON.stringify(n.parameters, null, 2)}</pre>
                  </div>
                </>
              );
            })()}
          </aside>
        )}
      </div>
    </div>
  );
}

export function WorkflowGraphView(props: Props) {
  return (
    <ReactFlowProvider>
      <GraphCanvas {...props} />
    </ReactFlowProvider>
  );
}
