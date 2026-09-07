#!/usr/bin/env python3
"""Smoke-verify core API flow with mock provider."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "be"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def wait_generation(client: TestClient, generation_id: int, timeout: float = 12.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = client.get(f"/api/v1/generations/{generation_id}")
        res.raise_for_status()
        data = res.json()
        if data["status"] in {"completed", "failed"}:
            return data
        time.sleep(0.5)
    raise TimeoutError(f"generation {generation_id} did not finish")


def main() -> None:
    client = TestClient(app)
    health = client.get("/api/v1/health")
    assert health.status_code == 200, health.text

    projects = client.get("/api/v1/projects").json()
    if not projects:
        raise SystemExit("No projects. Run scripts/seed_demo.py first.")
    project_id = projects[0]["id"]
    scenes = client.get(f"/api/v1/projects/{project_id}/scenes").json()
    assert scenes, "No scenes"
    scene_id = scenes[0]["id"]

    spec = client.post(f"/api/v1/scenes/{scene_id}/shot-spec/suggest")
    assert spec.status_code == 200, spec.text
    shot_spec_id = spec.json()["id"]

    key = client.post(
        f"/api/v1/scenes/{scene_id}/generations",
        json={"generation_type": "keyframe", "shot_spec_id": shot_spec_id},
    )
    assert key.status_code == 202, key.text
    key_job = wait_generation(client, key.json()["generation_id"])
    assert key_job["status"] == "completed", key_job
    assert key_job["assets"], "keyframe produced no asset"

    ref_id = key_job["assets"][0]["id"]
    vid = client.post(
        f"/api/v1/scenes/{scene_id}/generations",
        json={
            "generation_type": "image_to_video",
            "shot_spec_id": shot_spec_id,
            "reference_asset_id": ref_id,
            "duration_seconds": 4,
        },
    )
    assert vid.status_code == 202, vid.text
    vid_job = wait_generation(client, vid.json()["generation_id"], timeout=15)
    assert vid_job["status"] == "completed", vid_job

    asset_id = vid_job["assets"][0]["id"]
    review = client.post(
        f"/api/v1/assets/{asset_id}/reviews",
        json={"decision": "rejected", "comment": "Camera motion is too aggressive."},
    )
    assert review.status_code == 201, review.text

    rerun = client.post(f"/api/v1/generations/{vid_job['id']}/rerun")
    assert rerun.status_code == 202, rerun.text
    child = wait_generation(client, rerun.json()["generation_id"], timeout=15)
    assert child["parent_generation_id"] == vid_job["id"]
    assert child["seed"] == vid_job["seed"]
    assert child["id"] != vid_job["id"]

    # Original remains
    original = client.get(f"/api/v1/generations/{vid_job['id']}").json()
    assert original["status"] == "completed"

    print("verify_demo OK")
    print(f"  keyframe=#{key_job['id']} video=#{vid_job['id']} child=#{child['id']}")


if __name__ == "__main__":
    main()
