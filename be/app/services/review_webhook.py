"""Outbound review event for n8n (fire-and-forget; never blocks review)."""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings
from app.models import Asset, Review

logger = logging.getLogger(__name__)


def emit_asset_reviewed(
    *,
    asset: Asset,
    review: Review,
    project_id: int | None = None,
    scene_id: int | None = None,
) -> None:
    settings = get_settings()
    url = (settings.n8n_review_webhook_url or "").strip()
    if not url:
        return

    payload = {
        "event": "asset.reviewed",
        "asset_id": asset.id,
        "project_id": project_id,
        "scene_id": scene_id,
        "asset_type": asset.asset_type,
        "decision": review.decision,
        "reviewer": review.reviewer_name,
        "review_comment": review.comment,
        "provenance_url": f"/assets?asset={asset.id}",
    }
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
        logger.info("n8n asset.reviewed delivered for asset %s → %s", asset.id, url)
    except Exception:
        logger.exception("n8n webhook failed for asset %s (review still saved)", asset.id)
