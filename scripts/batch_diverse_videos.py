#!/usr/bin/env python3
"""Batch-generate 12+ diverse ComfyUI videos into Project Aurora on prod-agent-dev BE :8001 ONLY (not sibling :8000)."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Ensure scripts/ is importable when run as `python scripts/batch_diverse_videos.py`
sys.path.insert(0, str(Path(__file__).resolve().parent))
from log_paths import log_path  # noqa: E402

BASE = "http://127.0.0.1:8001/api/v1"
# Log naming: logs/YYYYMMDD_HHMM_<slug>.<ext> (Asia/Seoul)
OUT = log_path("batch_diverse_videos_report", ext="json")



def req(method: str, path: str, body: dict | None = None, timeout: int = 180):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    last_err: Exception | None = None
    for attempt in range(10):
        r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else None
        except (urllib.error.URLError, TimeoutError, ConnectionResetError) as exc:
            last_err = exc
            time.sleep(min(2**attempt, 15))
    assert last_err is not None
    raise last_err


def poll_generation(gen_id: int, label: str, timeout_s: int = 1200) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        g = req("GET", f"/generations/{gen_id}")
        status = g["status"]
        print(
            f"  [{label}] gen={gen_id} status={status} "
            f"provider={g.get('provider')} elapsed={time.time() - t0:.0f}s",
            flush=True,
        )
        if status in {"completed", "failed"}:
            return g
        time.sleep(5)
    raise TimeoutError(f"{label} generation {gen_id} timed out")


# 12 diverse drama-previs clips — distinct location / time / motion / mood for RAG recall.
SCENES = [
    {
        "scene_no": 31,
        "title": "Neon Alley Chase",
        "brief": "A fictional runner dashes through a rain-slick neon alley at night while the camera tracks laterally.",
        "shot": {
            "location": "neon rain alley",
            "time_of_day": "night",
            "subjects": ["fictional runner silhouette"],
            "action": "sprints past glowing shop signs",
            "shot_size": "medium wide",
            "camera_angle": "low angle",
            "camera_motion": "lateral tracking",
            "lighting": "magenta and cyan neon reflections on wet asphalt",
            "mood": "urgent, kinetic",
            "visual_prompt": (
                "cinematic neon alley at night, wet asphalt reflecting magenta cyan lights, "
                "fictional runner silhouette mid-sprint, low angle, 16:9 film still, no logos"
            ),
            "motion_prompt": (
                "lateral tracking shot following a runner through neon rain alley, "
                "reflections sliding across wet ground, urgent kinetic motion"
            ),
        },
    },
    {
        "scene_no": 32,
        "title": "Foggy Pier Walk",
        "brief": "A detective walks along a foggy wooden pier at dawn; the camera dollies backward.",
        "shot": {
            "location": "foggy wooden pier",
            "time_of_day": "dawn",
            "subjects": ["detective in long coat"],
            "action": "walks toward the camera through fog",
            "shot_size": "wide",
            "camera_angle": "eye level",
            "camera_motion": "slow dolly-out",
            "lighting": "soft gray dawn light, fog diffusion",
            "mood": "melancholy, quiet",
            "visual_prompt": (
                "wide foggy wooden pier at dawn, detective in long coat walking toward camera, "
                "soft gray light, melancholy atmosphere, 16:9 cinematic still"
            ),
            "motion_prompt": (
                "slow dolly-out on foggy pier at dawn as detective walks forward, "
                "fog drifting, quiet melancholy motion"
            ),
        },
    },
    {
        "scene_no": 33,
        "title": "Hospital Corridor Night",
        "brief": "Empty hospital corridor at night with flickering fluorescents; handheld documentary feel.",
        "shot": {
            "location": "hospital corridor",
            "time_of_day": "night",
            "subjects": ["empty corridor, distant gurney"],
            "action": "camera advances down the hallway",
            "shot_size": "wide",
            "camera_angle": "eye level",
            "camera_motion": "handheld forward walk",
            "lighting": "cold fluorescent flicker",
            "mood": "uneasy, clinical",
            "visual_prompt": (
                "empty hospital corridor at night, cold fluorescent lights, distant gurney, "
                "uneasy clinical mood, 16:9 film still, no readable text"
            ),
            "motion_prompt": (
                "handheld documentary forward walk down empty hospital corridor at night, "
                "fluorescent flicker, uneasy clinical motion"
            ),
        },
    },
    {
        "scene_no": 34,
        "title": "Desert Highway Heatwave",
        "brief": "A lone car on a desert highway under harsh noon sun; slow crane rise.",
        "shot": {
            "location": "desert highway",
            "time_of_day": "noon",
            "subjects": ["lone sedan"],
            "action": "drives into heat shimmer",
            "shot_size": "extreme wide",
            "camera_angle": "high angle",
            "camera_motion": "slow crane up",
            "lighting": "harsh noon sun, heat haze",
            "mood": "bleak, vast",
            "visual_prompt": (
                "extreme wide desert highway at noon, lone sedan, heat shimmer, "
                "harsh sunlight, bleak vast mood, 16:9 cinematic still"
            ),
            "motion_prompt": (
                "slow crane up over desert highway as a lone car drives into heat haze, "
                "bleak vast cinematic motion"
            ),
        },
    },
    {
        "scene_no": 35,
        "title": "Library Stacks Whisper",
        "brief": "Warm afternoon light through tall library windows; slow push into book stacks.",
        "shot": {
            "location": "old library stacks",
            "time_of_day": "afternoon",
            "subjects": ["rows of bookshelves"],
            "action": "dust motes drift in sunbeams",
            "shot_size": "medium",
            "camera_angle": "eye level",
            "camera_motion": "slow push-in",
            "lighting": "warm window shafts, soft dust",
            "mood": "intimate, scholarly",
            "visual_prompt": (
                "old library book stacks in warm afternoon light, dust motes in sunbeams, "
                "intimate scholarly mood, 16:9 film still"
            ),
            "motion_prompt": (
                "slow push-in through library stacks with warm window light and drifting dust, "
                "intimate scholarly motion"
            ),
        },
    },
    {
        "scene_no": 36,
        "title": "Snow Forest Tracking",
        "brief": "Winter forest at dusk; camera tracks beside footprints in fresh snow.",
        "shot": {
            "location": "snowy forest",
            "time_of_day": "dusk",
            "subjects": ["footprints in snow"],
            "action": "tracks along a path between pines",
            "shot_size": "wide",
            "camera_angle": "eye level",
            "camera_motion": "side tracking",
            "lighting": "blue dusk, soft snowfall",
            "mood": "lonely, cold",
            "visual_prompt": (
                "snowy pine forest at dusk, footprints in fresh snow, soft snowfall, "
                "lonely cold atmosphere, 16:9 cinematic still"
            ),
            "motion_prompt": (
                "side tracking shot along snowy forest path at dusk following footprints, "
                "soft snowfall, lonely cold motion"
            ),
        },
    },
    {
        "scene_no": 37,
        "title": "Kitchen Morning Light",
        "brief": "Quiet kitchen at sunrise; steam rises from a kettle as the camera pans.",
        "shot": {
            "location": "domestic kitchen",
            "time_of_day": "morning",
            "subjects": ["kettle with steam"],
            "action": "morning light fills the room",
            "shot_size": "medium",
            "camera_angle": "eye level",
            "camera_motion": "slow pan left",
            "lighting": "warm sunrise through curtains",
            "mood": "calm, domestic",
            "visual_prompt": (
                "quiet domestic kitchen at sunrise, steam from kettle, warm curtain light, "
                "calm domestic mood, 16:9 film still"
            ),
            "motion_prompt": (
                "slow pan across morning kitchen with rising kettle steam and warm sunrise light, "
                "calm domestic motion"
            ),
        },
    },
    {
        "scene_no": 38,
        "title": "Warehouse Spotlight Interrogation",
        "brief": "Dim warehouse with a single hard spotlight; slow orbit around a chair.",
        "shot": {
            "location": "warehouse interior",
            "time_of_day": "night",
            "subjects": ["empty metal chair"],
            "action": "spotlight holds on the chair",
            "shot_size": "medium",
            "camera_angle": "slight high angle",
            "camera_motion": "slow orbit",
            "lighting": "single hard spotlight, deep shadows",
            "mood": "threatening, tense",
            "visual_prompt": (
                "dim warehouse at night, empty metal chair under hard spotlight, deep shadows, "
                "threatening tense mood, 16:9 cinematic still"
            ),
            "motion_prompt": (
                "slow orbit around a spotlighted metal chair in a dark warehouse, "
                "threatening tense cinematic motion"
            ),
        },
    },
    {
        "scene_no": 39,
        "title": "Coastal Cliff Wind",
        "brief": "Windy coastal cliff at golden hour; camera tilts up from rocks to horizon.",
        "shot": {
            "location": "coastal cliff",
            "time_of_day": "golden hour",
            "subjects": ["cliff edge, ocean horizon"],
            "action": "wind moves tall grass",
            "shot_size": "wide",
            "camera_angle": "low angle",
            "camera_motion": "tilt up",
            "lighting": "golden hour sun, ocean glare",
            "mood": "epic, windswept",
            "visual_prompt": (
                "coastal cliff at golden hour, tall grass in wind, ocean horizon, "
                "epic windswept mood, 16:9 film still"
            ),
            "motion_prompt": (
                "tilt up from rocky cliff edge to ocean horizon at golden hour, "
                "grass whipping in wind, epic windswept motion"
            ),
        },
    },
    {
        "scene_no": 40,
        "title": "Underground Parking Lot",
        "brief": "Fluorescent underground parking garage; slow tracking past concrete pillars.",
        "shot": {
            "location": "underground parking garage",
            "time_of_day": "night",
            "subjects": ["concrete pillars, parked cars"],
            "action": "camera moves between rows",
            "shot_size": "wide",
            "camera_angle": "eye level",
            "camera_motion": "slow tracking forward",
            "lighting": "sickly fluorescent overhead",
            "mood": "cold, anonymous",
            "visual_prompt": (
                "underground parking garage with fluorescent lights, concrete pillars, "
                "parked cars, cold anonymous mood, 16:9 cinematic still, no logos"
            ),
            "motion_prompt": (
                "slow forward tracking through underground parking garage past concrete pillars, "
                "fluorescent flicker, cold anonymous motion"
            ),
        },
    },
    {
        "scene_no": 41,
        "title": "Temple Courtyard Rain",
        "brief": "Stone temple courtyard in soft rain; gentle crane down toward puddles.",
        "shot": {
            "location": "stone temple courtyard",
            "time_of_day": "overcast day",
            "subjects": ["stone lanterns, rain puddles"],
            "action": "rain ripples across stone",
            "shot_size": "wide",
            "camera_angle": "high angle",
            "camera_motion": "slow crane down",
            "lighting": "soft overcast, wet stone sheen",
            "mood": "serene, contemplative",
            "visual_prompt": (
                "stone temple courtyard in soft rain, lanterns, puddles on stone, "
                "serene contemplative mood, 16:9 film still"
            ),
            "motion_prompt": (
                "slow crane down over rainy temple courtyard toward rippling puddles, "
                "serene contemplative motion"
            ),
        },
    },
    {
        "scene_no": 42,
        "title": "Train Window Landscape",
        "brief": "Passenger POV looking out a train window at dusk countryside; subtle camera sway.",
        "shot": {
            "location": "train window interior",
            "time_of_day": "dusk",
            "subjects": ["window frame, blurred countryside"],
            "action": "landscape streams past",
            "shot_size": "close medium",
            "camera_angle": "eye level",
            "camera_motion": "subtle handheld sway",
            "lighting": "warm cabin light vs cool dusk outside",
            "mood": "nostalgic, transient",
            "visual_prompt": (
                "train window at dusk, warm cabin light, cool countryside blur outside, "
                "nostalgic transient mood, 16:9 cinematic still"
            ),
            "motion_prompt": (
                "subtle handheld sway at train window as dusk countryside streams past, "
                "nostalgic transient motion"
            ),
        },
    },
]


def find_or_create_project() -> dict:
    projects = req("GET", "/projects")
    for p in projects:
        if p.get("name") == "Project Aurora":
            return p
    return req(
        "POST",
        "/projects",
        {
            "name": "Project Aurora",
            "description": "Drama previsualization sandbox for Production Agent.",
            "status": "active",
        },
    )


def find_or_create_scene(project_id: int, spec: dict) -> dict:
    scenes = req("GET", f"/projects/{project_id}/scenes")
    for s in scenes:
        if s.get("scene_no") == spec["scene_no"] and s.get("title") == spec["title"]:
            return s
    return req(
        "POST",
        f"/projects/{project_id}/scenes",
        {
            "episode_no": 3,
            "scene_no": spec["scene_no"],
            "title": spec["title"],
            "brief": spec["brief"],
        },
    )


def ensure_shot_spec(scene_id: int, shot: dict) -> dict:
    existing = req("GET", f"/scenes/{scene_id}/shot-specs")
    if existing:
        return existing[-1]
    return req("POST", f"/scenes/{scene_id}/shot-specs", shot)


def first_asset(gen: dict, want: str | None = None) -> dict | None:
    assets = gen.get("assets") or []
    if want:
        for a in assets:
            if a.get("asset_type") == want:
                return a
    return assets[0] if assets else None


def already_approved_video(scene_id: int) -> dict | None:
    gens = req("GET", f"/scenes/{scene_id}/generations")
    for g in sorted(gens, key=lambda x: x["id"], reverse=True):
        if g.get("generation_type") != "image_to_video" or g.get("status") != "completed":
            continue
        for a in g.get("assets") or []:
            if a.get("asset_type") != "video":
                continue
            # Check reviews via asset reviews endpoint if present; fall back to dash later.
            return {"generation": g, "asset": a}
    return None


def run_one(project_id: int, spec: dict, seed_base: int) -> dict:
    title = spec["title"]
    print(f"\n=== {title} (scene_no={spec['scene_no']}) ===", flush=True)
    scene = find_or_create_scene(project_id, spec)
    shot = ensure_shot_spec(scene["id"], spec["shot"])
    result: dict = {
        "title": title,
        "scene_id": scene["id"],
        "scene_no": spec["scene_no"],
        "shot_spec_id": shot["id"],
    }

    # Keyframe
    kf_acc = req(
        "POST",
        f"/scenes/{scene['id']}/generations",
        {
            "generation_type": "keyframe",
            "shot_spec_id": shot["id"],
            "seed": seed_base,
        },
    )
    kf = poll_generation(kf_acc["generation_id"], f"{title}/keyframe")
    if kf["status"] != "completed":
        result["error"] = f"keyframe failed: {kf.get('error_code')} {kf.get('error_message')}"
        return result
    kf_asset = first_asset(kf, "keyframe")
    if not kf_asset:
        result["error"] = "keyframe completed but no asset"
        return result
    result["keyframe_generation_id"] = kf["id"]
    result["keyframe_asset_id"] = kf_asset["id"]

    # Video
    vid_acc = req(
        "POST",
        f"/scenes/{scene['id']}/generations",
        {
            "generation_type": "image_to_video",
            "shot_spec_id": shot["id"],
            "reference_asset_id": kf_asset["id"],
            "seed": seed_base + 17,
            "duration_seconds": 4.0,
        },
    )
    vid = poll_generation(vid_acc["generation_id"], f"{title}/video")
    if vid["status"] != "completed":
        result["error"] = f"video failed: {vid.get('error_code')} {vid.get('error_message')}"
        return result
    vid_asset = first_asset(vid, "video")
    if not vid_asset:
        result["error"] = "video completed but no asset"
        return result
    result["video_generation_id"] = vid["id"]
    result["video_asset_id"] = vid_asset["id"]
    result["video_url"] = vid_asset.get("url")
    result["provider"] = vid.get("provider")
    result["model_name"] = vid.get("model_name")

    # Approve → auto-index for RAG
    review = req(
        "POST",
        f"/assets/{vid_asset['id']}/reviews",
        {
            "decision": "approved",
            "comment": f"Batch diversity pack — approved for MediaRAG corpus ({title}).",
            "reviewer_name": "batch-script",
        },
    )
    result["review_id"] = review["id"]
    result["decision"] = review["decision"]

    # Explicit embed if needed
    try:
        emb = req("POST", f"/assets/{vid_asset['id']}/embeddings", {})
        result["embedding"] = {
            "id": emb.get("id") if isinstance(emb, dict) else None,
            "model_name": emb.get("model_name") if isinstance(emb, dict) else None,
            "raw_keys": list(emb.keys()) if isinstance(emb, dict) else type(emb).__name__,
        }
    except Exception as exc:  # noqa: BLE001
        result["embedding_error"] = str(exc)

    print(
        f"  OK video_asset={vid_asset['id']} review={review['id']} "
        f"provider={vid.get('provider')}",
        flush=True,
    )
    return result


def main() -> int:
    ready = req("GET", "/ready")
    print("READY", ready, flush=True)
    if ready.get("generation_provider") != "comfyui":
        print("ERROR: generation_provider is not comfyui", file=sys.stderr)
        return 1
    if "agents_sdk_enabled" not in ready:
        print("ERROR: not prod-agent-dev BE fingerprint (need agents_sdk_enabled on :8001)", file=sys.stderr)
        return 1

    project = find_or_create_project()
    print(f"PROJECT id={project['id']} name={project['name']}", flush=True)

    results = []
    t0 = time.time()
    for i, spec in enumerate(SCENES):
        try:
            row = run_one(project["id"], spec, seed_base=50000 + i * 137)
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {spec['title']}: {exc}", flush=True)
            row = {"title": spec["title"], "scene_no": spec["scene_no"], "error": str(exc)}
        results.append(row)
        ok = sum(1 for r in results if r.get("video_asset_id") and not r.get("error"))
        print(f"Progress: {ok}/{len(results)} videos ok", flush=True)

    # RAG smoke
    smoke = {"queries": []}
    try:
        from app.database import SessionLocal  # type: ignore
        from app.services.retrieval_service import RetrievalService  # type: ignore

        # Prefer HTTP-less in-process when run from be/; else skip.
    except Exception:
        SessionLocal = None  # type: ignore

    report = {
        "ready": ready,
        "project_id": project["id"],
        "elapsed_sec": round(time.time() - t0, 1),
        "requested": len(SCENES),
        "completed_videos": sum(
            1 for r in results if r.get("video_asset_id") and not r.get("error")
        ),
        "results": results,
        "dashboard": req("GET", "/dashboard"),
        "smoke": smoke,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT}", flush=True)
    print(
        f"DONE completed_videos={report['completed_videos']}/{report['requested']} "
        f"elapsed={report['elapsed_sec']}s",
        flush=True,
    )
    return 0 if report["completed_videos"] >= 10 else 2


if __name__ == "__main__":
    raise SystemExit(main())
