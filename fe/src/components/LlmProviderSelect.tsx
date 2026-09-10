import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type LlmProviderId = "openai" | "ollama" | "hf" | "mock";

export type LlmOption = {
  id: LlmProviderId | string;
  label: string;
  default_model: string;
  notes?: string;
  available?: boolean;
};

const FALLBACK: LlmOption[] = [
  { id: "openai", label: "OpenAI", default_model: "gpt-4o-mini" },
  { id: "ollama", label: "Ollama Qwen3-8B", default_model: "qwen3:8b" },
  { id: "hf", label: "HF Qwen3-8B", default_model: "Qwen/Qwen3-8B" },
  { id: "mock", label: "Mock", default_model: "mock" },
];

type Props = {
  value: LlmProviderId;
  onChange: (v: LlmProviderId) => void;
  options?: LlmOption[] | null;
  className?: string;
  label?: string;
};

export function LlmProviderSelect({
  value,
  onChange,
  options,
  className,
  label = "LLM",
}: Props) {
  const opts = options?.length ? options : FALLBACK;
  return (
    <div className={cn("flex flex-wrap items-center gap-2 text-sm", className)}>
      <span className="text-muted-foreground">{label}</span>
      {opts.map((opt) => {
        const id = opt.id as LlmProviderId;
        const active = value === id;
        const disabled = opt.available === false && id !== "mock";
        return (
          <button
            key={opt.id}
            type="button"
            disabled={disabled}
            title={opt.notes || opt.default_model}
            onClick={() => onChange(id)}
          >
            <Badge
              variant={active ? "success" : "outline"}
              className={cn(disabled && "opacity-40")}
            >
              {opt.label}
            </Badge>
          </button>
        );
      })}
    </div>
  );
}
