#!/usr/bin/env python3
"""Download Qwen3-8B from Hugging Face and serve an OpenAI-compatible /v1 API.

Usage (from repo root, with be/.venv activated):
  python scripts/download_hf_agent_model.py
  python scripts/serve_hf_llm.py --host 0.0.0.0 --port 8002

Requires HF_TOKEN in .env (or environment). Does not print the token.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_env_token() -> str:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or ""
    if token:
        return token.strip()
    env_path = ROOT / ".env"
    if env_path.exists():
        m = re.search(r"^HF_TOKEN=(.*)$", env_path.read_text(), re.M)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Qwen/Qwen3-8B")
    parser.add_argument(
        "--local-dir",
        default=str(ROOT / "models" / "Qwen3-8B"),
    )
    args = parser.parse_args()

    token = _load_env_token()
    if not token:
        print("ERROR: HF_TOKEN missing in env/.env", file=sys.stderr)
        return 1

    os.environ["HF_TOKEN"] = token
    os.environ["HUGGING_FACE_HUB_TOKEN"] = token

    from huggingface_hub import snapshot_download

    local_dir = Path(args.local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {args.repo} → {local_dir} …", flush=True)
    path = snapshot_download(
        repo_id=args.repo,
        token=token,
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
    )
    print(f"DOWNLOADED {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
