import { useMemo, useRef, useState } from "react";
import { FileText, Image as ImageIcon, Upload, Video } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/api/client";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { formatRelativeTime } from "@/lib/utils";
import type { Asset } from "@/types";

type Tab = "all" | "images" | "videos" | "documents";

const TABS: { id: Tab; label: string }[] = [
  { id: "all", label: "All" },
  { id: "images", label: "Images" },
  { id: "videos", label: "Videos" },
  { id: "documents", label: "Documents" },
];

function formatBytes(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function AssetsPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("all");
  const [ingestionFilter, setIngestionFilter] = useState<string>("");
  const [selected, setSelected] = useState<Asset | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const assets = useQuery({
    queryKey: ["assets", tab, ingestionFilter],
    queryFn: () =>
      api.listAssets({
        tab,
        ingestion_status: ingestionFilter || undefined,
      }),
  });

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadDocument(file),
    onSuccess: () => {
      toast.success("Document uploaded (pending ingestion)");
      qc.invalidateQueries({ queryKey: ["assets"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e: Error) => toast.error(e.message || "Upload failed"),
  });

  const ingest = useMutation({
    mutationFn: () => api.runAssetIngestion(),
    onSuccess: (run) => {
      toast.success(
        `Ingestion ${run.status}: ${run.records_processed} processed, ${run.records_failed} failed`,
      );
      qc.invalidateQueries({ queryKey: ["assets"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e: Error) => toast.error(e.message || "Ingestion failed"),
  });

  const sorted = useMemo(
    () =>
      [...(assets.data || [])].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      ),
    [assets.data],
  );

  return (
    <div>
      <PageHeader
        title="Assets"
        description="Production asset library — images, videos, and documents (ops ETL, not document RAG)."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.md,.csv,.pdf,text/plain,text/markdown,text/csv,application/pdf"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) upload.mutate(f);
                e.target.value = "";
              }}
            />
            <Button
              variant="secondary"
              size="sm"
              onClick={() => fileRef.current?.click()}
              disabled={upload.isPending}
            >
              <Upload className="mr-1.5 h-4 w-4" />
              Upload document
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => ingest.mutate()}
              disabled={ingest.isPending}
            >
              Run ingestion
            </Button>
          </div>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {TABS.map((t) => (
          <Button
            key={t.id}
            size="sm"
            variant={tab === t.id ? "default" : "outline"}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </Button>
        ))}
        {(tab === "documents" || tab === "all") && (
          <select
            className="ml-auto h-9 rounded-md border border-border bg-background px-2 text-sm"
            value={ingestionFilter}
            onChange={(e) => setIngestionFilter(e.target.value)}
            aria-label="Ingestion status filter"
          >
            <option value="">Any ingestion status</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="processed">Processed</option>
            <option value="failed">Failed</option>
          </select>
        )}
      </div>

      {assets.isLoading && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="aspect-video rounded-lg" />
          ))}
        </div>
      )}

      {!assets.isLoading && sorted.length === 0 && (
        <Card className="p-10 text-center">
          <p className="text-sm font-medium">No assets yet</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Generate media from a scene, or upload a production document and run ingestion.
          </p>
        </Card>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {sorted.map((a) => {
          const isDoc = a.asset_type === "document";
          return (
            <button
              key={a.id}
              type="button"
              onClick={() => setSelected(a)}
              className="group text-left"
            >
              <Card className="overflow-hidden transition-colors hover:border-white/14">
                <div className="relative aspect-video bg-black/40">
                  {isDoc ? (
                    <div className="flex h-full flex-col items-center justify-center gap-2 px-3 text-muted-foreground">
                      <FileText className="h-8 w-8" />
                      <span className="line-clamp-2 text-center text-xs">
                        {a.original_filename || `Document #${a.id}`}
                      </span>
                    </div>
                  ) : a.url ? (
                    a.mime_type.startsWith("video/") ? (
                      <video src={a.url} className="h-full w-full object-contain" muted />
                    ) : (
                      <img
                        src={a.url}
                        alt={`Asset ${a.id}`}
                        className="h-full w-full object-contain"
                      />
                    )
                  ) : (
                    <div className="flex h-full items-center justify-center text-muted-foreground">
                      {a.asset_type.includes("video") ? (
                        <Video className="h-8 w-8" />
                      ) : (
                        <ImageIcon className="h-8 w-8" />
                      )}
                    </div>
                  )}
                  <div className="absolute left-2 top-2 flex gap-1">
                    <Badge variant="outline">{a.asset_type}</Badge>
                    {a.ingestion_status && (
                      <Badge variant="info">{a.ingestion_status}</Badge>
                    )}
                  </div>
                </div>
                <CardContent className="space-y-1 p-3">
                  <div className="truncate text-sm font-medium">
                    {isDoc
                      ? a.original_filename || `Document #${a.id}`
                      : `Asset #${a.id}`}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {isDoc
                      ? `${a.mime_type} · ${formatBytes(a.file_size)} · ${formatRelativeTime(a.created_at)}`
                      : `Job ${a.generation_job_id ?? "—"} · ${formatRelativeTime(a.created_at)}`}
                  </div>
                </CardContent>
              </Card>
            </button>
          );
        })}
      </div>

      <Sheet open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <SheetContent>
          {selected && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold">
                  {selected.asset_type === "document"
                    ? selected.original_filename || `Document #${selected.id}`
                    : `Asset #${selected.id}`}
                </h2>
                <p className="text-sm text-muted-foreground">
                  {selected.asset_type} · {selected.mime_type}
                </p>
              </div>
              {selected.asset_type !== "document" && selected.url && (
                <div className="overflow-hidden rounded-md border border-border bg-black">
                  {selected.mime_type.startsWith("video/") ? (
                    <video src={selected.url} controls className="w-full" />
                  ) : (
                    <img
                      src={selected.url}
                      alt={`Asset ${selected.id}`}
                      className="w-full object-contain"
                    />
                  )}
                </div>
              )}
              {selected.asset_type === "document" && selected.extracted_text && (
                <pre className="max-h-64 overflow-auto rounded-md border border-border bg-black/40 p-3 text-xs whitespace-pre-wrap">
                  {selected.extracted_text.slice(0, 4000)}
                </pre>
              )}
              <dl className="space-y-2 text-sm">
                {selected.generation_job_id != null && (
                  <div className="flex justify-between gap-4">
                    <dt className="text-muted-foreground">Generation job</dt>
                    <dd className="font-mono">#{selected.generation_job_id}</dd>
                  </div>
                )}
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">Status</dt>
                  <dd>{selected.status}</dd>
                </div>
                {selected.ingestion_status && (
                  <div className="flex justify-between gap-4">
                    <dt className="text-muted-foreground">Ingestion</dt>
                    <dd>{selected.ingestion_status}</dd>
                  </div>
                )}
                {selected.source && (
                  <div className="flex justify-between gap-4">
                    <dt className="text-muted-foreground">Source</dt>
                    <dd>{selected.source}</dd>
                  </div>
                )}
                {selected.file_size != null && (
                  <div className="flex justify-between gap-4">
                    <dt className="text-muted-foreground">Size</dt>
                    <dd>{formatBytes(selected.file_size)}</dd>
                  </div>
                )}
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">Checksum</dt>
                  <dd className="font-mono text-xs">
                    {(selected.checksum || "").slice(0, 16)}
                    {selected.checksum ? "…" : "—"}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">Path</dt>
                  <dd className="max-w-[220px] break-all font-mono text-xs text-muted-foreground">
                    {selected.file_path}
                  </dd>
                </div>
                {selected.duration_seconds != null && (
                  <div className="flex justify-between gap-4">
                    <dt className="text-muted-foreground">Duration</dt>
                    <dd>{selected.duration_seconds}s</dd>
                  </div>
                )}
                {selected.processed_at && (
                  <div className="flex justify-between gap-4">
                    <dt className="text-muted-foreground">Processed</dt>
                    <dd>{formatRelativeTime(selected.processed_at)}</dd>
                  </div>
                )}
              </dl>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
