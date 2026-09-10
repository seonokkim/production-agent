#!/usr/bin/env python3
"""Seed Project Aurora demo data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "be"))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Project, Scene  # noqa: E402
from app.services.workflow_service import ensure_default_workflows  # noqa: E402


def main() -> None:
    demo_path = ROOT / "data" / "demo" / "project-aurora.json"
    demo = json.loads(demo_path.read_text(encoding="utf-8"))

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_workflows(db)
        existing = db.query(Project).filter(Project.name == demo["project"]["name"]).first()
        if existing:
            print(f"Project already exists: id={existing.id}")
            scene = (
                db.query(Scene)
                .filter(Scene.project_id == existing.id, Scene.title == demo["scene"]["title"])
                .first()
            )
            if scene:
                print(f"Scene already exists: id={scene.id}")
                print(f"Open http://localhost:5173/scenes/{scene.id}")
                return
            project = existing
        else:
            project = Project(
                name=demo["project"]["name"],
                description=demo["project"]["description"],
            )
            db.add(project)
            db.commit()
            db.refresh(project)

        scene = Scene(
            project_id=project.id,
            title=demo["scene"]["title"],
            episode_no=demo["scene"]["episode_no"],
            scene_no=demo["scene"]["scene_no"],
            brief=demo["scene"]["brief"],
            status="draft",
        )
        db.add(scene)
        db.commit()
        db.refresh(scene)
        print(f"Seeded project={project.id} scene={scene.id}")
        print(f"Open http://localhost:5173/scenes/{scene.id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
