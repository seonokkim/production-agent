"""ComfyUI provider adapter — wraps HTTP API; never called from the frontend."""

from __future__ import annotations

import copy
import hashlib
import logging
import shutil
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

# Match CreateVideo fps in comfy/workflows/i2v_v1.json
_I2V_FPS = 24


class ComfyUIProvider(GenerationProvider):
    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.comfyui_base_url).rstrip("/")
        self._output_dir = Path(settings.asset_storage_path) / "outputs"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._client_id = f"production-agent-{uuid.uuid4().hex[:8]}"
        self._comfy_input_dir = Path(
            getattr(settings, "comfyui_input_dir", "")
            or "/home/work/.workspace/ComfyUI/input"
        )
        self._comfy_input_dir.mkdir(parents=True, exist_ok=True)
        self._asset_root = Path(settings.asset_storage_path)

    def submit(self, request: GenerationRequest) -> ProviderSubmitResult:
        workflow = self._inject(request)
        payload = {"prompt": workflow, "client_id": self._client_id}
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(f"{self.base_url}/prompt", json=payload)
                if resp.status_code >= 400:
                    detail = resp.text[:500]
                    raise RuntimeError(f"COMFYUI_SUBMIT_FAILED HTTP {resp.status_code}: {detail}")
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.exception("ComfyUI submit failed")
            raise RuntimeError(f"COMFYUI_SUBMIT_FAILED: {exc}") from exc

        if data.get("node_errors"):
            raise RuntimeError(f"COMFYUI_NODE_ERRORS: {data['node_errors']}")

        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"COMFYUI_INVALID_RESPONSE: missing prompt_id ({data})")
        return ProviderSubmitResult(provider_job_id=str(prompt_id), status=ProviderStatus.QUEUED)

    def get_status(self, provider_job_id: str) -> ProviderStatusResult:
        try:
            with httpx.Client(timeout=60.0) as client:
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
            if status_str == "success":
                return ProviderStatusResult(
                    status=ProviderStatus.FAILED,
                    error_code="COMFYUI_NO_OUTPUT",
                    error_message="History success but empty outputs.",
                )
            return ProviderStatusResult(status=ProviderStatus.RUNNING, progress=0.7)

        saved = self._fetch_outputs(outputs, provider_job_id)
        if not saved:
            return ProviderStatusResult(
                status=ProviderStatus.FAILED,
                error_code="COMFYUI_NO_OUTPUT",
                error_message=f"History completed but no fetchable outputs: {list(outputs.keys())}",
            )
        return ProviderStatusResult(status=ProviderStatus.COMPLETED, outputs=saved, progress=1.0)

    def cancel(self, provider_job_id: str) -> bool:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(f"{self.base_url}/interrupt")
                return resp.status_code < 400
        except httpx.HTTPError:
            return False

    def _inject(self, request: GenerationRequest) -> dict:
        workflow = copy.deepcopy(request.workflow_snapshot)
        node_map = request.node_map or {}

        width = request.width
        height = request.height
        if request.generation_type == "image_to_video" and height % 32:
            height = 704

        # Duration → Wan frame length (4n+1); fps matches CreateVideo in i2v_v1.json
        frame_count = None
        if request.duration_seconds:
            raw = max(17, int(round(float(request.duration_seconds) * _I2V_FPS)))
            frame_count = ((raw - 1) // 4) * 4 + 1

        mappings: dict[str, object] = {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "seed": request.seed,
            "width": width,
            "height": height,
        }
        if frame_count is not None:
            mappings["frame_count"] = frame_count

        if request.reference_file_path:
            mappings["reference_image"] = self._stage_reference_image(request.reference_file_path)

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

    def _stage_reference_image(self, relative_or_abs: str) -> str:
        """Copy app storage asset into ComfyUI/input and return the filename Comfy expects."""
        src = Path(relative_or_abs)
        if not src.is_absolute():
            src = self._asset_root / relative_or_abs
        if not src.exists():
            raise FileNotFoundError(f"Reference image not found: {src}")
        dest_name = f"pa_ref_{uuid.uuid4().hex[:10]}{src.suffix or '.png'}"
        dest = self._comfy_input_dir / dest_name
        shutil.copy2(src, dest)
        return dest_name

    def _fetch_outputs(self, outputs: dict, provider_job_id: str) -> list[ProviderOutput]:
        results: list[ProviderOutput] = []
        seen: set[str] = set()
        with httpx.Client(timeout=120.0) as client:
            for node_out in outputs.values():
                candidates = []
                for key in ("images", "gifs", "videos"):
                    candidates.extend(node_out.get(key) or [])
                if isinstance(node_out.get("video"), list):
                    candidates.extend(node_out["video"])
                for item in candidates:
                    if not isinstance(item, dict):
                        continue
                    filename = item.get("filename")
                    if not filename:
                        continue
                    params = {
                        "filename": filename,
                        "subfolder": item.get("subfolder", ""),
                        "type": item.get("type", "output"),
                    }
                    key = f"{params['subfolder']}/{filename}"
                    if key in seen:
                        continue
                    seen.add(key)
                    resp = client.get(f"{self.base_url}/view", params=params)
                    resp.raise_for_status()
                    data = resp.content
                    ext = Path(filename).suffix.lower() or ".png"
                    name = f"{provider_job_id}{ext}"
                    path = self._output_dir / name
                    path.write_bytes(data)
                    if ext in {".mp4", ".webm", ".mov", ".mkv", ".avi"}:
                        mime = "video/mp4" if ext == ".mp4" else f"video/{ext.lstrip('.')}"
                        asset_type = "video"
                    elif ext in {".webp", ".gif"} and len(data) > 200_000:
                        mime = "image/webp" if ext == ".webp" else "image/gif"
                        asset_type = "video"
                    else:
                        mime = {
                            ".png": "image/png",
                            ".jpg": "image/jpeg",
                            ".jpeg": "image/jpeg",
                            ".webp": "image/webp",
                        }.get(ext, "application/octet-stream")
                        asset_type = "keyframe"
                    results.append(
                        ProviderOutput(
                            file_path=f"outputs/{name}",
                            mime_type=mime,
                            asset_type=asset_type,
                            checksum=hashlib.sha256(data).hexdigest(),
                        )
                    )
        return results
