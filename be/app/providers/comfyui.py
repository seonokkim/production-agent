"""ComfyUI provider adapter — wraps HTTP API; never called from the frontend."""

from __future__ import annotations

import copy
import hashlib
import logging
import uuid
from pathlib import Path

import httpx

from app.config import get_settings
from app.providers.base import (
    GenerationProvider,
    GenerationRequest,
    ProviderOutput,
    ProviderStatus,
    ProviderStatusResult,
    ProviderSubmitResult,
)

logger = logging.getLogger(__name__)


class ComfyUIProvider(GenerationProvider):
    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.comfyui_base_url).rstrip("/")
        self._output_dir = Path(settings.asset_storage_path) / "outputs"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._client_id = f"production-agent-{uuid.uuid4().hex[:8]}"

    def submit(self, request: GenerationRequest) -> ProviderSubmitResult:
        workflow = self._inject(request)
        payload = {"prompt": workflow, "client_id": self._client_id}
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(f"{self.base_url}/prompt", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.exception("ComfyUI submit failed")
            raise RuntimeError(f"COMFYUI_SUBMIT_FAILED: {exc}") from exc

        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError("COMFYUI_INVALID_RESPONSE: missing prompt_id")
        return ProviderSubmitResult(provider_job_id=str(prompt_id), status=ProviderStatus.QUEUED)

    def get_status(self, provider_job_id: str) -> ProviderStatusResult:
        try:
            with httpx.Client(timeout=30.0) as client:
                hist = client.get(f"{self.base_url}/history/{provider_job_id}")
                hist.raise_for_status()
                history = hist.json()
        except httpx.HTTPError as exc:
            return ProviderStatusResult(
                status=ProviderStatus.FAILED,
                error_code="COMFYUI_STATUS_FAILED",
                error_message=str(exc),
            )

        if provider_job_id not in history:
            return ProviderStatusResult(status=ProviderStatus.RUNNING, progress=0.4)

        entry = history[provider_job_id]
        status_str = (entry.get("status") or {}).get("status_str", "")
        if status_str == "error":
            return ProviderStatusResult(
                status=ProviderStatus.FAILED,
                error_code="COMFYUI_EXECUTION_ERROR",
                error_message=str(entry.get("status")),
            )

        outputs = entry.get("outputs") or {}
        if not outputs:
            return ProviderStatusResult(status=ProviderStatus.RUNNING, progress=0.7)

        saved = self._fetch_outputs(outputs, provider_job_id)
        if not saved:
            return ProviderStatusResult(
                status=ProviderStatus.FAILED,
                error_code="COMFYUI_NO_OUTPUT",
                error_message="History completed but no fetchable outputs.",
            )
        return ProviderStatusResult(status=ProviderStatus.COMPLETED, outputs=saved, progress=1.0)

    def _inject(self, request: GenerationRequest) -> dict:
        workflow = copy.deepcopy(request.workflow_snapshot)
        node_map = request.node_map or {}
        mappings = {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "seed": request.seed,
            "width": request.width,
            "height": request.height,
        }
        for key, value in mappings.items():
            target = node_map.get(key)
            if not target:
                continue
            node_id = str(target["node_id"])
            input_name = target["input"]
            if node_id not in workflow:
                raise ValueError(f"Node {node_id} missing for inject key {key}")
            workflow[node_id].setdefault("inputs", {})[input_name] = value
        return workflow

    def _fetch_outputs(self, outputs: dict, provider_job_id: str) -> list[ProviderOutput]:
        results: list[ProviderOutput] = []
        settings = get_settings()
        with httpx.Client(timeout=60.0) as client:
            for node_out in outputs.values():
                for image in node_out.get("images", []):
                    params = {
                        "filename": image["filename"],
                        "subfolder": image.get("subfolder", ""),
                        "type": image.get("type", "output"),
                    }
                    resp = client.get(f"{self.base_url}/view", params=params)
                    resp.raise_for_status()
                    data = resp.content
                    ext = Path(image["filename"]).suffix or ".png"
                    name = f"{provider_job_id}{ext}"
                    path = self._output_dir / name
                    path.write_bytes(data)
                    rel = f"outputs/{name}"
                    mime = "image/png" if ext.lower() in {".png", ".jpg", ".jpeg", ".webp"} else "video/mp4"
                    asset_type = "video" if mime.startswith("video") else "keyframe"
                    results.append(
                        ProviderOutput(
                            file_path=rel,
                            mime_type=mime,
                            asset_type=asset_type,
                            checksum=hashlib.sha256(data).hexdigest(),
                        )
                    )
                for video in node_out.get("gifs", []) + node_out.get("videos", []):
                    filename = video.get("filename")
                    if not filename:
                        continue
                    params = {
                        "filename": filename,
                        "subfolder": video.get("subfolder", ""),
                        "type": video.get("type", "output"),
                    }
                    resp = client.get(f"{self.base_url}/view", params=params)
                    resp.raise_for_status()
                    data = resp.content
                    ext = Path(filename).suffix or ".mp4"
                    name = f"{provider_job_id}{ext}"
                    path = self._output_dir / name
                    path.write_bytes(data)
                    results.append(
                        ProviderOutput(
                            file_path=f"outputs/{name}",
                            mime_type="video/mp4",
                            asset_type="video",
                            checksum=hashlib.sha256(data).hexdigest(),
                        )
                    )
        _ = settings
        return results
