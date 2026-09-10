export type WorkflowGraphNode = {
  id: string;
  class_type: string;
  label: string;
  category: string;
  parameters: Record<string, string | number | boolean | null>;
};

export type WorkflowGraphEdge = {
  source: string;
  source_output: number;
  target: string;
  target_input: string;
};

export type WorkflowGraph = {
  workflow_name: string | null;
  workflow_version: string | null;
  workflow_type: string | null;
  workflow_hash: string | null;
  model_name: string | null;
  model_version: string | null;
  source: string;
  frozen: boolean;
  generation_id: number | null;
  node_count: number;
  edge_count: number;
  nodes: WorkflowGraphNode[];
  edges: WorkflowGraphEdge[];
  read_only: boolean;
};

export type WorkflowViewerMode =
  | { kind: "active"; workflowName: "keyframe_v1" | "i2v_v1" }
  | { kind: "generation"; generationId: number };
