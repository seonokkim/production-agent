#!/usr/bin/env python3
"""Evaluate Approved Reference Retrieval: Hit@3, MRR, latency."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "be"))

from app.database import SessionLocal  # noqa: E402
from app.models import Asset, AssetEmbedding  # noqa: E402
from app.schemas import ReferenceSearchRequest  # noqa: E402
from app.services.retrieval_service import RetrievalService  # noqa: E402


def main() -> None:
    corpus = json.loads((ROOT / "data" / "retrieval" / "corpus.json").read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        # Map clip_id -> asset_embedding via asset checksum (seed stores clip id there).
        emb_by_clip: dict[str, int] = {}
        for emb in db.query(AssetEmbedding).all():
            asset = db.get(Asset, emb.asset_id)
            if asset and asset.checksum:
                emb_by_clip[asset.checksum] = emb.id

        if not emb_by_clip:
            raise SystemExit("No embeddings found. Run scripts/seed_retrieval_corpus.py first.")

        from app.models import GenerationJob, Scene

        scene = db.query(Scene).filter(Scene.title == "Retrieval Corpus").first()
        if not scene:
            emb0 = db.query(AssetEmbedding).first()
            asset0 = db.get(Asset, emb0.asset_id) if emb0 else None
            job0 = db.get(GenerationJob, asset0.generation_job_id) if asset0 else None
            scene_id = job0.scene_id if job0 else None
        else:
            scene_id = scene.id
        if not scene_id:
            raise SystemExit("Cannot resolve scene_id for search")

        retrieval = RetrievalService()
        hits_at_3 = 0
        mrr_total = 0.0
        latencies: list[int] = []

        for query in corpus["queries"]:
            started = time.perf_counter()
            res = retrieval.search(
                db,
                scene_id,
                ReferenceSearchRequest(query_text=query["text"], top_k=3),
            )
            latency = int((time.perf_counter() - started) * 1000)
            latencies.append(res.latency_ms or latency)

            relevant = set(query["relevant_clip_ids"])
            ranked_clips: list[str] = []
            for hit in res.results:
                asset_row = db.get(Asset, hit.asset_id)
                if asset_row:
                    ranked_clips.append(asset_row.checksum)

            hit3 = any(c in relevant for c in ranked_clips[:3])
            hits_at_3 += int(hit3)
            rr = 0.0
            for idx, clip_id in enumerate(ranked_clips, start=1):
                if clip_id in relevant:
                    rr = 1.0 / idx
                    break
            mrr_total += rr
            print(
                f"{query['id']}: hit@3={hit3} rr={rr:.3f} latency_ms={res.latency_ms} "
                f"top={ranked_clips[:3]}"
            )

        n = len(corpus["queries"])
        print("---")
        print(f"Hit@3: {hits_at_3 / n:.3f} ({hits_at_3}/{n})")
        print(f"MRR:   {mrr_total / n:.3f}")
        print(f"Avg latency_ms: {sum(latencies) / len(latencies):.1f}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
