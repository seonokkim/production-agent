#!/usr/bin/env python3
"""Minimal OpenAI-compatible chat server for a local HF causal LM (Qwen3-8B).

Exposes:
  GET  /health
  GET  /v1/models
  POST /v1/chat/completions

Designed for OpenAI Agents SDK via OpenAIChatCompletionsModel(base_url=…).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

ROOT = Path(__file__).resolve().parents[1]


def _env_token() -> str:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or ""
    if token:
        return token.strip()
    env_path = ROOT / ".env"
    if env_path.exists():
        m = re.search(r"^HF_TOKEN=(.*)$", env_path.read_text(), re.M)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return ""


class ChatMessage(BaseModel):
    role: str
    content: str | list[Any] | None = ""


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    temperature: float = 0.2
    max_tokens: int | None = 1024
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any = None


def build_app(model_id: str, model_dir: Path, device: str = "auto") -> FastAPI:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    token = _env_token() or None
    print(f"Loading tokenizer/model from {model_dir} (id={model_id}) …", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(
        str(model_dir), trust_remote_code=True, token=token
    )
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        str(model_dir),
        trust_remote_code=True,
        token=token,
        torch_dtype=dtype,
        device_map=device if torch.cuda.is_available() else None,
    )
    if not torch.cuda.is_available():
        model = model.to("cpu")
    model.eval()
    print("HF LLM ready", flush=True)

    app = FastAPI(title="HF Local LLM", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "model": model_id}

    @app.get("/v1/models")
    def list_models():
        return {
            "object": "list",
            "data": [{"id": model_id, "object": "model", "owned_by": "local-hf"}],
        }

    def _msg_text(content: str | list[Any] | None) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        # OpenAI multimodal content parts — flatten text.
        parts = []
        for p in content:
            if isinstance(p, dict) and p.get("type") == "text":
                parts.append(str(p.get("text") or ""))
            else:
                parts.append(str(p))
        return "\n".join(parts)

    @app.post("/v1/chat/completions")
    def chat(req: ChatRequest):
        if not req.messages:
            raise HTTPException(400, "messages required")
        # Build chat template input; append /no_think for Qwen3 to keep latency low.
        messages = []
        for m in req.messages:
            role = m.role if m.role in {"system", "user", "assistant"} else "user"
            messages.append({"role": role, "content": _msg_text(m.content)})
        if messages and messages[-1]["role"] == "user":
            messages[-1]["content"] = (messages[-1]["content"] or "") + "\n/no_think"

        try:
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                tools=req.tools,
            )
        except TypeError:
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

        inputs = tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        max_new = int(req.max_tokens or 1024)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=max_new,
                do_sample=req.temperature > 0,
                temperature=max(req.temperature, 1e-5),
                pad_token_id=tokenizer.eos_token_id,
            )
        gen = out[0][inputs["input_ids"].shape[-1] :]
        text = tokenizer.decode(gen, skip_special_tokens=True)
        if "</think>" in text:
            text = text.split("</think>", 1)[-1].strip()

        cid = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        return {
            "id": cid,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model or model_id,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": int(inputs["input_ids"].shape[-1]),
                "completion_tokens": int(gen.shape[-1]),
                "total_tokens": int(inputs["input_ids"].shape[-1] + gen.shape[-1]),
            },
        }

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--model-id", default="Qwen/Qwen3-8B")
    parser.add_argument(
        "--model-dir",
        default=str(ROOT / "models" / "Qwen3-8B"),
    )
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    model_dir = Path(args.model_dir)
    if not model_dir.exists() or not any(model_dir.iterdir()):
        raise SystemExit(
            f"Model dir empty/missing: {model_dir}. Run scripts/download_hf_agent_model.py first."
        )
    app = build_app(args.model_id, model_dir, device=args.device)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
