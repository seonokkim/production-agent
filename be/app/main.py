"""Production Agent API entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import assets, dashboard, generations, projects, scenes, shot_specs
from app.config import get_settings
from app.database import Base, engine
from app.services.workflow_service import ensure_default_workflows


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    storage = Path(settings.asset_storage_path)
    (storage / "inputs").mkdir(parents=True, exist_ok=True)
    (storage / "outputs").mkdir(parents=True, exist_ok=True)
    Path(settings.database_url.replace("sqlite:///", "")).parent.mkdir(
        parents=True, exist_ok=True
    ) if settings.database_url.startswith("sqlite") else None
    Base.metadata.create_all(bind=engine)
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        ensure_default_workflows(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "Production-oriented AI Creation workflow for turning scene briefs "
            "into reviewable, reproducible image and video assets."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(scenes.router, prefix="/api/v1")
    app.include_router(shot_specs.router, prefix="/api/v1")
    app.include_router(generations.router, prefix="/api/v1")
    app.include_router(assets.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")

    storage = Path(settings.asset_storage_path)
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "inputs").mkdir(parents=True, exist_ok=True)
    (storage / "outputs").mkdir(parents=True, exist_ok=True)
    app.mount("/storage", StaticFiles(directory=str(storage)), name="storage")

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "app": settings.app_name, "env": settings.app_env}

    @app.get("/api/v1/ready")
    def ready():
        return {
            "status": "ready",
            "generation_provider": settings.generation_provider,
            "llm_provider": settings.llm_provider,
        }

    return app


app = create_app()
