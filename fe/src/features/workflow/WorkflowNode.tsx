import { Handle, Position, type NodeProps } from "@xyflow/react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { categoryAccent, type WorkflowNodeData } from "./workflowLayout";

function formatParam(value: string | number | boolean | null): string {
  if (value === null) return "null";
  if (typeof value === "string") {
    if (value.length > 72) return `"${value.slice(0, 71)}…"`;
    return value.includes("\n") || value.length > 40 ? `"${value}"` : value;
  }
  return String(value);
}

export function WorkflowNode({ data, selected }: NodeProps & { data: WorkflowNodeData }) {
  const node = data.graphNode;
  const [rawOpen, setRawOpen] = useState(false);
  const accent = categoryAccent(node.category);
  const entries = Object.entries(node.parameters || {});
  const preview = entries.slice(0, 4);
  const hasMore = entries.length > 4;

  return (
    <div
      className={cn(
        "w-[260px] rounded-lg border bg-[hsl(222_27%_8%)] shadow-md transition-shadow",
        selected ? "border-primary ring-2 ring-primary/40" : "border-border",
      )}
      style={{ borderLeftWidth: 3, borderLeftColor: accent }}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!h-2 !w-2 !border-border !bg-muted-foreground"
      />
      <div className="border-b border-border/60 px-3 py-2">
        <div className="text-sm font-medium leading-tight text-foreground">{node.label}</div>
        <div className="mt-0.5 font-mono text-[10px] text-muted-foreground">{node.class_type}</div>
      </div>
      <div className="space-y-1 px-3 py-2">
        {preview.length === 0 && (
          <div className="text-[11px] text-muted-foreground/70">No display parameters</div>
        )}
        {preview.map(([key, value]) => (
          <div key={key} className="flex gap-2 text-[11px] leading-snug">
            <span className="shrink-0 font-mono text-muted-foreground">{key}</span>
            <span className="min-w-0 break-words text-foreground/90">{formatParam(value)}</span>
          </div>
        ))}
        {(hasMore || entries.length > 0) && (
          <button
            type="button"
            className="mt-1 text-[10px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
            onClick={(e) => {
              e.stopPropagation();
              setRawOpen((v) => !v);
            }}
          >
            {rawOpen ? "Hide raw parameters" : "Raw parameters"}
          </button>
        )}
        {rawOpen && (
          <pre className="mt-1 max-h-36 overflow-auto rounded border border-border/50 bg-black/30 p-2 font-mono text-[10px] text-muted-foreground">
            {JSON.stringify(node.parameters, null, 2)}
          </pre>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-2 !w-2 !border-border !bg-muted-foreground"
      />
    </div>
  );
}
