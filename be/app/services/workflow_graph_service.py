"""Derive a read-only visualization graph from ComfyUI API-format workflows.

The API-format JSON under comfy/workflows/* remains the authoritative execution
representation. This module only inspects that structure for the GUI viewer.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.models import GenerationJob, WorkflowVersion

# Human-friendly titles for known class_types (actual classes only).
CLASS_LABELS: dict[str, str] = {
    "CheckpointLoaderSimple": "Load Checkpoint",
    "CLIPTextEncode": "Text Encode",
    "EmptyLatentImage": "Empty Latent",
    "KSampler": "Sampler",
    "VAEDecode": "VAE Decode",
    "SaveImage": "Save Image",
    "UNETLoader": "Load UNET",
    "CLIPLoader": "Load CLIP",
    "VAELoader": "Load VAE",
    "ModelSamplingSD3": "Model Sampling",
    "LoadImage": "Load Image",
    "Wan22ImageToVideoLatent": "Wan Image→Video Latent",
    "CreateVideo": "Create Video",
    "SaveVideo": "Save Video",
}

CLASS_CATEGORIES: dict[str, str] = {
    "CheckpointLoaderSimple": "model",
    "UNETLoader": "model",
    "CLIPLoader": "model",
    "VAELoader": "model",
    "ModelSamplingSD3": "model",
    "CLIPTextEncode": "prompt",
    "EmptyLatentImage": "latent",
    "Wan22ImageToVideoLatent": "latent",
    "KSampler": "sampler",
    "VAEDecode": "decode",
    "LoadImage": "io",
    "SaveImage": "io",
    "CreateVideo": "io",
    "SaveVideo": "io",
}

# Prefer these scalar inputs on node cards (order preserved).
DISPLAY_PRIORITY: dict[str, tuple[str, ...]] = {
    "CheckpointLoaderSimple": ("ckpt_name",),
    "UNETLoader": ("unet_name", "weight_dtype"),
    "CLIPLoader": ("clip_name", "type"),
    "VAELoader": ("vae_name",),
    "ModelSamplingSD3": ("shift",),
    "CLIPTextEncode": ("text",),
    "EmptyLatentImage": ("width", "height", "batch_size"),
    "Wan22ImageToVideoLatent": ("width", "height", "length", "batch_size"),
    "KSampler": (
        "seed",
        "steps",
        "cfg",
        "sampler_name",
        "scheduler",
        "denoise",
    ),
    "LoadImage": ("image",),
    "SaveImage": ("filename_prefix",),
    "CreateVideo": ("fps",),
    "SaveVideo": ("filename_prefix", "format", "codec"),
}

_SECRET_KEY_RE = re.compile(
    r"(token|secret|password|credential|api[_-]?key|hf[_-]?token|auth)",
    re.IGNORECASE,
)

_MAX_TEXT = 120


def _is_link(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and isinstance(value[0], (str, int))
        and isinstance(value[1], int)
    )


def _sanitize_key(key: str) -> bool:
    return not bool(_SECRET_KEY_RE.search(key))


def _display_value(value: Any) -> Any:
    if isinstance(value, str):
        if len(value) > _MAX_TEXT:
            return value[: _MAX_TEXT - 1] + "…"
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    # Nested non-link structures — stringify compactly for inspection.
    try:
        text = json.dumps(value, ensure_ascii=False)
    except TypeError:
        text = str(value)
    if len(text) > _MAX_TEXT:
        return text[: _MAX_TEXT - 1] + "…"
    return text


def _pick_parameters(class_type: str, inputs: dict[str, Any]) -> dict[str, Any]:
    scalars: dict[str, Any] = {}
    for key, value in inputs.items():
        if not _sanitize_key(key):
            continue
        if _is_link(value):
            continue
        scalars[key] = _display_value(value)

    priority = DISPLAY_PRIORITY.get(class_type, ())
    ordered: dict[str, Any] = {}
    for key in priority:
        if key in scalars:
            ordered[key] = scalars.pop(key)
    # Keep a few remaining scalars for unknown / extra fields (still safe).
    for key, value in list(scalars.items())[:6]:
        ordered[key] = value
    return ordered


def _label_for(class_type: str) -> str:
    if class_type in CLASS_LABELS:
        return CLASS_LABELS[class_type]
    # Fallback: split CamelCase / digits without inventing product names.
    spaced = re.sub(r"([a-z])([A-Z0-9])", r"\1 \2", class_type)
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    return spaced


def api_workflow_to_graph(
    workflow: dict[str, Any],
    *,
    workflow_name: str | None = None,
    workflow_version: str | None = None,
    workflow_hash: str | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    workflow_type: str | None = None,
    source: str = "active",
    generation_id: int | None = None,
    frozen: bool = False,
) -> dict[str, Any]:
    """Convert ComfyUI API-format prompt dict → normalized nodes + edges."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for node_id, raw in workflow.items():
        if not isinstance(raw, dict):
            continue
        class_type = str(raw.get("class_type") or "Unknown")
        inputs = raw.get("inputs") or {}
        if not isinstance(inputs, dict):
            inputs = {}

        nodes.append(
            {
                "id": str(node_id),
                "class_type": class_type,
                "label": _label_for(class_type),
                "category": CLASS_CATEGORIES.get(class_type, "other"),
                "parameters": _pick_parameters(class_type, inputs),
            }
        )

        for input_name, value in inputs.items():
            if not _is_link(value):
                continue
            source_id, source_output = value[0], value[1]
            edges.append(
                {
                    "source": str(source_id),
                    "source_output": int(source_output),
                    "target": str(node_id),
                    "target_input": str(input_name),
                }
            )

    # Stable ordering for deterministic UI / tests.
    nodes.sort(key=lambda n: int(n["id"]) if str(n["id"]).isdigit() else str(n["id"]))
    edges.sort(
        key=lambda e: (e["source"], e["target"], e["target_input"], e["source_output"])
    )

    computed_hash = workflow_hash
    if computed_hash is None:
        computed_hash = hashlib.sha256(
            json.dumps(workflow, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    return {
        "workflow_name": workflow_name,
        "workflow_version": workflow_version,
        "workflow_type": workflow_type,
        "workflow_hash": computed_hash,
        "model_name": model_name,
        "model_version": model_version,
        "source": source,
        "frozen": frozen,
        "generation_id": generation_id,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "read_only": True,
    }


def graph_from_workflow_version(wf: WorkflowVersion) -> dict[str, Any]:
    path = wf.workflow_path
    data = json.loads(open(path, encoding="utf-8").read())
    return api_workflow_to_graph(
        data,
        workflow_name=wf.name,
        workflow_version=wf.version,
        workflow_hash=wf.workflow_hash,
        model_name=wf.model_name,
        model_version=wf.model_version,
        workflow_type=wf.workflow_type,
        source="active",
        frozen=False,
    )


def graph_from_generation(job: GenerationJob) -> dict[str, Any]:
    try:
        snapshot = json.loads(job.workflow_snapshot_json or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid workflow_snapshot_json on generation {job.id}") from exc
    if not isinstance(snapshot, dict):
        raise ValueError(f"workflow_snapshot_json must be an object for generation {job.id}")

    wf = job.workflow_version
    return api_workflow_to_graph(
        snapshot,
        workflow_name=wf.name if wf else None,
        workflow_version=wf.version if wf else None,
        workflow_hash=wf.workflow_hash if wf else None,
        model_name=job.model_name or (wf.model_name if wf else None),
        model_version=job.model_version or (wf.model_version if wf else None),
        workflow_type=wf.workflow_type if wf else job.generation_type,
        source="generation_snapshot",
        generation_id=job.id,
        frozen=True,
    )
