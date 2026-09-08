#!/usr/bin/env python3
"""Seed synthetic approved video clips + embeddings for Approved Reference Retrieval."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "be"))

from app.config import get_settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Asset, GenerationJob, Project, Review, Scene, ShotSpec  # noqa: E402
from app.services.retrieval_service import RetrievalService  # noqa: E402
from app.services.workflow_service import ensure_default_workflows, get_active_workflow  # noqa: E402


def main() -> None:
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    corpus_path = ROOT / "data" / "retrieval" / "corpus.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    settings = get_settings()
    storage = Path(settings.asset_storage_path)
    retrieval_dir = storage / "retrieval"
    retrieval_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        ensure_default_workflows(db)
        project = db.query(Project).filter(Project.name == "Project Aurora").first()
        if not project:
            project = Project(name="Project Aurora", description="Retrieval seed project")
            db.add(project)
            db.commit()
            db.refresh(project)

        scene = (
            db.query(Scene)
            .filter(Scene.project_id == project.id, Scene.title == "Retrieval Corpus")
            .first()
        )
        if not scene:
            scene = Scene(
                project_id=project.id,
                title="Retrieval Corpus",
                episode_no=0,
                scene_no=0,
                brief="Synthetic public-domain style clips for reference retrieval eval.",
            )
            db.add(scene)
            db.commit()
            db.refresh(scene)

        workflow = get_active_workflow(db, "image_to_video")
        retrieval = RetrievalService()
        indexed = 0

        for clip in corpus["clips"]:
            rel_path = f"retrieval/{clip['id']}.svg"
            abs_path = storage / rel_path
            desc_path = abs_path.with_suffix(".txt")
            if not abs_path.exists():
                abs_path.write_text(
                    f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360">
  <rect width="100%" height="100%" fill="#1a2330"/>
  <text x="32" y="180" fill="#9bb0c3" font-size="22">{clip['title']}</text>
</svg>
""",
                    encoding="utf-8",
                )
            desc_path.write_text(clip["description"], encoding="utf-8")

            existing_asset = (
                db.query(Asset).filter(Asset.file_path == rel_path.replace("\\", "/")).first()
            )
            if existing_asset:
                continue

            shot = ShotSpec(
                scene_id=scene.id,
                version=(
                    (db.query(ShotSpec).filter(ShotSpec.scene_id == scene.id).count() or 0) + 1
                ),
                location=clip["location"],
                time_of_day="night" if "night" in clip["description"] else "day",
                subjects_json=json.dumps(["figure"]),
                action=clip["title"],
                shot_size="medium",
                camera_angle="eye level",
                camera_motion=clip["camera_motion"],
                lighting=clip["lighting"],
                mood=clip["mood"],
                visual_prompt=clip["description"],
                motion_prompt=clip["description"],
                source="manual",
            )
            db.add(shot)
            db.commit()
            db.refresh(shot)

            job = GenerationJob(
                scene_id=scene.id,
                shot_spec_id=shot.id,
                workflow_version_id=workflow.id,
                generation_type="image_to_video",
                provider="mock",
                status="completed",
                prompt=clip["description"],
                negative_prompt="",
                model_name=workflow.model_name,
                model_version=workflow.model_version,
                seed=1000 + indexed,
                width=1280,
                height=720,
                duration_seconds=4.0,
                fps=24,
                frame_count=96,
                workflow_snapshot_json="{}",
                configuration_json=json.dumps(
                    {
                        "location": clip["location"],
                        "lighting": clip["lighting"],
                        "mood": clip["mood"],
                        "camera_motion": clip["camera_motion"],
                        "clip_id": clip["id"],
                    }
                ),
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            asset = Asset(
                generation_job_id=job.id,
                asset_type="video",
                file_path=rel_path.replace("\\", "/"),
                mime_type="image/svg+xml",
                checksum=clip["id"],
                width=1280,
                height=720,
                duration_seconds=4.0,
                status="ready",
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)

            db.add(
                Review(
                    asset_id=asset.id,
                    decision="approved",
                    comment="Seed corpus approval",
                    reviewer_name="seed",
                )
            )
            db.commit()
            retrieval.index_asset(db, asset.id, require_approved=True)
            indexed += 1

        print(f"Seeded/indexed retrieval corpus clips={indexed} scene_id={scene.id}")
        print(f"Queries available: {len(corpus['queries'])} in {corpus_path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
