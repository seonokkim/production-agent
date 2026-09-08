"""Multimodal RAG tool implementations (shared by mock + live Agents path)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session, joinedload

from app.models import Asset, AssetEmbedding, GenerationJob, Review, Scene, ShotSpec
from app.providers import get_embedding_provider
from app.services.retrieval_service import cosine_similarity


@dataclass
class CiteHit:
    cite_key: str
    asset_id: int
    asset_embedding_id: int | None
    media_type: str
    score: float
    t_start: float | None
    t_end: float | None
    thumb_url: str | None
    poster_url: str | None
    segment_note: str
    snippets: list[str]

    def to_tool_dict(self) -> dict:
        d = asdict(self)
        return d


def is_approved(db: Session, asset_id: int) -> bool:
    row = (
        db.query(Review)
        .filter(Review.asset_id == asset_id, Review.decision == "approved")
        .order_by(Review.id.desc())
        .first()
    )
    return row is not None


def media_kind(asset: Asset) -> str:
    if asset.asset_type == "video" or (asset.mime_type or "").startswith("video/"):
        return "video"
    return "image"


def cite_key(asset_id: int, embedding_id: int | None) -> str:
    return f"c{asset_id}-e{embedding_id or 0}"


def multimodal_search(
    db: Session,
    *,
    query: str,
    project_id: int | None = None,
    media_type: str = "any",
    top_n: int = 5,
    embedding_provider: str | None = None,
) -> list[CiteHit]:
    provider = get_embedding_provider(embedding_provider)
    query_emb = provider.embed_text(query)
    # Prefer provider.last_used (mock|marengo|mock-fallback…); else model name.
    used = getattr(provider, "last_used", None) or query_emb.model_name
    multimodal_search.last_embedding_used = used  # type: ignore[attr-defined]
    multimodal_search.last_embedding_model = query_emb.model_name  # type: ignore[attr-defined]

    rows = (
        db.query(AssetEmbedding)
        .options(
            joinedload(AssetEmbedding.asset)
            .joinedload(Asset.generation_job)
            .joinedload(GenerationJob.workflow_version)
        )
        .all()
    )

    scored: list[CiteHit] = []
    for row in rows:
        asset = row.asset
        if not asset or not is_approved(db, row.asset_id):
            continue
        kind = media_kind(asset)
        if media_type != "any" and kind != media_type:
            continue
        if project_id is not None:
            job = asset.generation_job
            if not job or not job.scene_id:
                continue
            scene = db.get(Scene, job.scene_id)
            if not scene or scene.project_id != project_id:
                continue

        score = cosine_similarity(query_emb.vector, list(row.embedding))
        url = f"/storage/{asset.file_path}"
        note = ""
        t_start = row.segment_start_sec
        t_end = row.segment_end_sec
        if kind == "video":
            note = "asset-level match"
            if t_start is None:
                t_start = 0.0
            if t_end is None:
                t_end = asset.duration_seconds

        snippets: list[str] = []
        job = asset.generation_job
        if job:
            if job.prompt:
                snippets.append(job.prompt[:160])
            shot = db.get(ShotSpec, job.shot_spec_id)
            if shot:
                bits = [shot.location, shot.lighting, shot.mood, shot.camera_motion]
                snippets.append(" · ".join(b for b in bits if b))

        scored.append(
            CiteHit(
                cite_key=cite_key(asset.id, row.id),
                asset_id=asset.id,
                asset_embedding_id=row.id,
                media_type=kind,
                score=round(score, 6),
                t_start=t_start if kind == "video" else None,
                t_end=t_end if kind == "video" else None,
                thumb_url=url,
                poster_url=url if kind == "video" else None,
                segment_note=note,
                snippets=[s for s in snippets if s],
            )
        )

    scored.sort(key=lambda h: h.score, reverse=True)
    return scored[:top_n]


def get_asset_content(db: Session, cite_key_value: str, mode: str = "summary") -> dict:
    """Return ShotSpec / review / path metadata for a cite_key (no huge binaries)."""
    asset_id, emb_id = _parse_cite_key(cite_key_value)
    asset = db.get(Asset, asset_id)
    if not asset:
        return {"error": f"Unknown asset for {cite_key_value}"}
    if not is_approved(db, asset_id):
        return {"error": "Asset is not approved"}

    job = db.get(GenerationJob, asset.generation_job_id) if asset.generation_job_id else None
    shot = db.get(ShotSpec, job.shot_spec_id) if job else None
    review = (
        db.query(Review)
        .filter(Review.asset_id == asset_id, Review.decision == "approved")
        .order_by(Review.id.desc())
        .first()
    )

    payload: dict = {
        "cite_key": cite_key_value,
        "asset_id": asset_id,
        "asset_embedding_id": emb_id or None,
        "media_type": media_kind(asset),
        "mime_type": asset.mime_type,
        "file_path": asset.file_path,
        "duration_seconds": asset.duration_seconds,
        "review_comment": review.comment if review else None,
    }
    if shot:
        payload["shot_spec"] = {
            "location": shot.location,
            "lighting": shot.lighting,
            "mood": shot.mood,
            "camera_motion": shot.camera_motion,
            "subject": shot.subject,
        }
    if job and mode == "full":
        payload["prompt"] = job.prompt
        payload["workflow_snapshot"] = (job.workflow_snapshot_json or "")[:500]
    elif job:
        payload["prompt_preview"] = (job.prompt or "")[:200]
    return payload


def get_video_segment(
    db: Session,
    cite_key_value: str,
    *,
    t_start: float | None = None,
    t_end: float | None = None,
    mode: str = "metadata",
) -> dict:
    content = get_asset_content(db, cite_key_value, mode="summary")
    if content.get("error"):
        return content
    if content.get("media_type") != "video":
        return {**content, "note": "Not a video asset; returning asset metadata only."}

    asset = db.get(Asset, content["asset_id"])
    assert asset is not None
    start = t_start if t_start is not None else 0.0
    end = t_end if t_end is not None else (asset.duration_seconds or start)
    poster = f"/storage/{asset.file_path}"
    return {
        "cite_key": cite_key_value,
        "asset_id": asset.id,
        "media_type": "video",
        "t_start": start,
        "t_end": end,
        "poster_url": poster,
        "mode": mode,
        "note": "asset-level match (fine-grained Marengo segments not required for MVP)",
        "metadata": content,
    }


def compose_answer(query: str, hits: list[CiteHit]) -> str:
    if not hits:
        return (
            f"No approved media matched “{query}”. "
            "Approve and index more stills/video, then retry."
        )
    lines = [
        f"Found {len(hits)} approved reference(s) for “{query}”.",
        "Citations (must be reviewed by a human before generation):",
    ]
    for hit in hits:
        cite = f"[{hit.media_type}:{hit.cite_key}]"
        if hit.media_type == "video":
            seg = f" asset-level ({hit.t_start}s–{hit.t_end}s)" if hit.segment_note else ""
            lines.append(f"- {cite} video score={hit.score}{seg}")
        else:
            lines.append(f"- {cite} image score={hit.score}")
    lines.append("Attach selected cites into a scene to freeze provenance.")
    return "\n".join(lines)


def hits_to_json(hits: list[CiteHit]) -> str:
    return json.dumps([h.to_tool_dict() for h in hits], ensure_ascii=False)


def _parse_cite_key(value: str) -> tuple[int, int]:
    # format: c{asset_id}-e{embedding_id}
    try:
        left, right = value.split("-e", 1)
        asset_id = int(left.lstrip("c"))
        emb_id = int(right)
        return asset_id, emb_id
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid cite_key: {value}") from exc
