"""Mock generation provider for GPU-free demos and tests."""

from __future__ import annotations

import hashlib
import time
import uuid
from pathlib import Path

from app.config import get_settings
from app.providers.base import (
    GenerationProvider,
    GenerationRequest,
    ProviderOutput,
    ProviderStatus,
    ProviderStatusResult,
    ProviderSubmitResult,
)


class MockProvider(GenerationProvider):
    """Simulates queued → running → completed with deterministic placeholder assets."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        settings = get_settings()
        self._output_dir = Path(settings.asset_storage_path) / "outputs"
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def submit(self, request: GenerationRequest) -> ProviderSubmitResult:
        job_id = f"mock-{uuid.uuid4().hex[:12]}"
        self._jobs[job_id] = {
            "request": request,
            "submitted_at": time.time(),
            "status": ProviderStatus.QUEUED,
        }
        return ProviderSubmitResult(provider_job_id=job_id, status=ProviderStatus.QUEUED)

    def get_status(self, provider_job_id: str) -> ProviderStatusResult:
        job = self._jobs.get(provider_job_id)
        if not job:
            return ProviderStatusResult(
                status=ProviderStatus.FAILED,
                error_code="PROVIDER_JOB_NOT_FOUND",
                error_message=f"Unknown mock job {provider_job_id}",
            )

        request: GenerationRequest = job["request"]
        elapsed = time.time() - job["submitted_at"]

        if request.force_fail and elapsed >= 1.0:
            job["status"] = ProviderStatus.FAILED
            return ProviderStatusResult(
                status=ProviderStatus.FAILED,
                error_code="MOCK_CONTROLLED_FAILURE",
                error_message="Controlled mock failure for demo/reliability rehearsal.",
            )

        # keyframe ~2s, video ~4s
        running_after = 0.4
        complete_after = 2.0 if request.generation_type == "keyframe" else 4.0

        if elapsed < running_after:
            job["status"] = ProviderStatus.QUEUED
            return ProviderStatusResult(status=ProviderStatus.QUEUED, progress=0.1)

        if elapsed < complete_after:
            job["status"] = ProviderStatus.RUNNING
            progress = min(0.95, elapsed / complete_after)
            return ProviderStatusResult(status=ProviderStatus.RUNNING, progress=progress)

        if "output" not in job:
            job["output"] = self._write_placeholder(request, provider_job_id)

        job["status"] = ProviderStatus.COMPLETED
        return ProviderStatusResult(
            status=ProviderStatus.COMPLETED,
            outputs=[job["output"]],
            progress=1.0,
        )

    def _write_placeholder(self, request: GenerationRequest, job_id: str) -> ProviderOutput:
        if request.generation_type == "keyframe":
            content = self._svg_keyframe(request)
            ext = "svg"
            mime = "image/svg+xml"
            asset_type = "keyframe"
            duration = None
        else:
            content = self._svg_video_poster(request)
            ext = "svg"
            mime = "image/svg+xml"
            asset_type = "video"
            duration = request.duration_seconds or 4.0

        rel = f"outputs/{job_id}.{ext}"
        path = self._output_dir / f"{job_id}.{ext}"
        path.write_text(content, encoding="utf-8")
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return ProviderOutput(
            file_path=rel,
            mime_type=mime,
            asset_type=asset_type,
            width=request.width,
            height=request.height,
            duration_seconds=duration,
            checksum=checksum,
        )

    def _svg_keyframe(self, request: GenerationRequest) -> str:
        prompt = (request.prompt or "keyframe")[:120].replace("<", "")
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{request.width}" height="{request.height}" viewBox="0 0 {request.width} {request.height}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0b1a2b"/>
      <stop offset="55%" stop-color="#12304a"/>
      <stop offset="100%" stop-color="#2a0f2e"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#g)"/>
  <text x="48" y="64" fill="#9ad7ff" font-family="Georgia, serif" font-size="28">AI-generated keyframe (mock)</text>
  <text x="48" y="120" fill="#e8f1ff" font-family="monospace" font-size="16">seed={request.seed}</text>
  <foreignObject x="48" y="160" width="{request.width - 96}" height="200">
    <div xmlns="http://www.w3.org/1999/xhtml" style="color:#d7e6f7;font:16px/1.4 Georgia,serif;">{prompt}</div>
  </foreignObject>
</svg>
"""

    def _svg_video_poster(self, request: GenerationRequest) -> str:
        prompt = (request.prompt or "video")[:120].replace("<", "")
        dur = request.duration_seconds or 4.0
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{request.width}" height="{request.height}" viewBox="0 0 {request.width} {request.height}">
  <rect width="100%" height="100%" fill="#101820"/>
  <circle cx="{request.width // 2}" cy="{request.height // 2}" r="48" fill="#2dd4bf" fill-opacity="0.85"/>
  <polygon points="{request.width // 2 - 12},{request.height // 2 - 20} {request.width // 2 - 12},{request.height // 2 + 20} {request.width // 2 + 22},{request.height // 2}" fill="#041016"/>
  <text x="48" y="64" fill="#99f6e4" font-family="Georgia, serif" font-size="28">AI-generated video poster (mock)</text>
  <text x="48" y="110" fill="#cbd5e1" font-family="monospace" font-size="16">duration={dur}s seed={request.seed}</text>
  <foreignObject x="48" y="150" width="{request.width - 96}" height="180">
    <div xmlns="http://www.w3.org/1999/xhtml" style="color:#e2e8f0;font:16px/1.4 Georgia,serif;">{prompt}</div>
  </foreignObject>
</svg>
"""
