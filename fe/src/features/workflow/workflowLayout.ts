import dagre from "@dagrejs/dagre";
import type { Edge, Node } from "@xyflow/react";
import type { WorkflowGraph, WorkflowGraphNode } from "./workflowTypes";

export const NODE_WIDTH = 260;
export const NODE_HEIGHT = 120;

export type WorkflowNodeData = {
  graphNode: WorkflowGraphNode;
};

const CATEGORY_ACCENT: Record<string, string> = {
  model: "hsl(247 70% 62%)",
  prompt: "hsl(168 45% 42%)",
  latent: "hsl(210 70% 55%)",
  sampler: "hsl(38 80% 52%)",
  decode: "hsl(280 40% 55%)",
  io: "hsl(142 40% 42%)",
  other: "hsl(220 8% 45%)",
};

export function categoryAccent(category: string): string {
  return CATEGORY_ACCENT[category] || CATEGORY_ACCENT.other;
}

type DagreGraph = {
  setDefaultEdgeLabel: (fn: () => Record<string, never>) => void;
  setGraph: (graph: Record<string, unknown>) => void;
  setNode: (id: string, value: { width: number; height: number }) => void;
  setEdge: (source: string, target: string) => void;
  hasNode: (id: string) => boolean;
  node: (id: string) => { x: number; y: number; width: number; height: number };
};

export function layoutWorkflowGraph(graph: WorkflowGraph): {
  nodes: Node<WorkflowNodeData>[];
  edges: Edge[];
} {
  const g = new dagre.graphlib.Graph() as unknown as DagreGraph;
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({
    rankdir: "TB",
    nodesep: 48,
    ranksep: 72,
    marginx: 24,
    marginy: 24,
  });

  for (const n of graph.nodes) {
    const paramLines = Object.keys(n.parameters || {}).length;
    const height = Math.min(220, NODE_HEIGHT + paramLines * 16);
    g.setNode(n.id, { width: NODE_WIDTH, height });
  }
  for (const e of graph.edges) {
    if (!g.hasNode(e.source) || !g.hasNode(e.target)) continue;
    g.setEdge(e.source, e.target);
  }

  dagre.layout(g as never);

  const nodes: Node<WorkflowNodeData>[] = graph.nodes.map((n) => {
    const pos = g.node(n.id);
    const height = pos.height || NODE_HEIGHT;
    return {
      id: n.id,
      type: "workflow",
      position: {
        x: (pos.x || 0) - NODE_WIDTH / 2,
        y: (pos.y || 0) - height / 2,
      },
      data: { graphNode: n },
      draggable: false,
      connectable: false,
    };
  });

  const edges: Edge[] = graph.edges.map((e, idx) => ({
    id: `e-${e.source}-${e.target}-${e.target_input}-${idx}`,
    source: e.source,
    target: e.target,
    label: e.target_input,
    type: "smoothstep",
    animated: false,
    style: { stroke: "hsl(222 14% 32%)", strokeWidth: 1.5 },
    labelStyle: {
      fill: "hsl(220 8% 62%)",
      fontSize: 10,
      fontFamily: "ui-monospace, monospace",
    },
    labelBgStyle: { fill: "hsl(222 27% 7%)", fillOpacity: 0.9 },
    labelBgPadding: [4, 2] as [number, number],
    labelBgBorderRadius: 4,
  }));

  return { nodes, edges };
}
