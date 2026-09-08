import { useMemo, useState } from "react";
import { Image as ImageIcon, Video } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { formatRelativeTime } from "@/lib/utils";
import type { Asset } from "@/types";

export function AssetsPage() {
  const assets = useQuery({ queryKey: ["assets"], queryFn: api.listAssets });
  const [selected, setSelected] = useState<Asset | null>(null);

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
        description="Approved and generated media library. Technical paths live in detail."
      />

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
            Generate a keyframe from a scene workspace to populate the library.
          </p>
        </Card>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {sorted.map((a) => (
          <button
            key={a.id}
            type="button"
            onClick={() => setSelected(a)}
            className="group text-left"
          >
            <Card className="overflow-hidden transition-colors hover:border-white/14">
              <div className="relative aspect-video bg-black/40">
                {a.url ? (
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
                <div className="absolute left-2 top-2">
                  <Badge variant="outline">{a.asset_type}</Badge>
                </div>
              </div>
              <CardContent className="space-y-1 p-3">
                <div className="text-sm font-medium">Asset #{a.id}</div>
                <div className="text-xs text-muted-foreground">
                  Job {a.generation_job_id} · {formatRelativeTime(a.created_at)}
                </div>
              </CardContent>
            </Card>
          </button>
        ))}
      </div>

      <Sheet open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <SheetContent>
          {selected && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold">Asset #{selected.id}</h2>
                <p className="text-sm text-muted-foreground">
                  {selected.asset_type} · {selected.mime_type}
                </p>
              </div>
              {selected.url && (
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
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">Generation job</dt>
                  <dd className="font-mono">#{selected.generation_job_id}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">Status</dt>
                  <dd>{selected.status}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">Checksum</dt>
                  <dd className="font-mono text-xs">{selected.checksum.slice(0, 16)}…</dd>
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
              </dl>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
