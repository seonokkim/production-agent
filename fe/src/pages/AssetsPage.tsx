import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function AssetsPage() {
  const assets = useQuery({ queryKey: ["assets"], queryFn: api.listAssets });

  return (
    <div>
      <h1>Asset / generation history</h1>
      <p className="muted">All generated assets remain immutable. AI-generated label applies.</p>
      {assets.isLoading && <p className="muted">Loading…</p>}
      <div className="panel">
        {assets.data?.map((a) => (
          <div className="history-item" key={a.id}>
            <div>#{a.id}</div>
            <div>
              <div>
                {a.asset_type} · job {a.generation_job_id}
              </div>
              <div className="muted">{a.file_path}</div>
              <div className="muted">AI-generated · checksum {a.checksum.slice(0, 12)}…</div>
            </div>
            <div>
              {a.url && (
                <a href={a.url} target="_blank" rel="noreferrer">
                  Open
                </a>
              )}
            </div>
          </div>
        ))}
        {assets.data?.length === 0 && <p className="muted">No assets yet.</p>}
      </div>
    </div>
  );
}
