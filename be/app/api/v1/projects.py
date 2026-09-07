from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, Scene
from app.schemas import ProjectCreate, ProjectRead, SceneCreate, SceneRead

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.id.desc()).all()


@router.post("/projects", response_model=ProjectRead, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/scenes", response_model=list[SceneRead])
def list_project_scenes(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(Scene)
        .filter(Scene.project_id == project_id)
        .order_by(Scene.episode_no, Scene.scene_no, Scene.id)
        .all()
    )


@router.post("/projects/{project_id}/scenes", response_model=SceneRead, status_code=201)
def create_scene(project_id: int, payload: SceneCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    scene = Scene(
        project_id=project_id,
        title=payload.title,
        episode_no=payload.episode_no,
        scene_no=payload.scene_no,
        brief=payload.brief,
    )
    db.add(scene)
    db.commit()
    db.refresh(scene)
    return scene
