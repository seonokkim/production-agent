"""Production Agent API entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import agents, assets, dashboard, generations, llm, projects, retrieval, scenes, shot_specs, workflows
from app.config import get_settings
from app.database import Base, get_db  # noqa: F401
from app import database as db_module
from app.services.workflow_service import ensure_default_workflows


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    storage = Path(settings.asset_storage_path)
    (storage / "inputs").mkdir(parents=True, exist_ok=True)
    (storage / "outputs").mkdir(parents=True, exist_ok=True)
    (storage / "documents").mkdir(parents=True, exist_ok=True)
    Path(settings.asset_landing_path).mkdir(parents=True, exist_ok=True)
    Path(settings.database_url.replace("sqlite:///", "")).parent.mkdir(
        parents=True, exist_ok=True
    ) if settings.database_url.startswith("sqlite") else None
    # Ensure model metadata is registered (incl. P1 retrieval tables).
    import app.models  # noqa: F401

    if settings.database_url.startswith("postgresql"):
        from sqlalchemy import text

        with db_module.engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(bind=db_module.engine)
    from app.agents.schema_ensure import ensure_agent_conversation_schema
    from app.services.schema_ensure_assets import ensure_asset_ops_schema

    ensure_agent_conversation_schema()
    ensure_asset_ops_schema()
    db = db_module.SessionLocal()
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
    app.include_router(retrieval.router, prefix="/api/v1")
    app.include_router(agents.router, prefix="/api/v1")
    app.include_router(llm.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")
    app.include_router(workflows.router, prefix="/api/v1")

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
        settings = get_settings()
        from app.agents.model_provider import list_agent_llm_options, resolve_agent_llm_provider, resolve_agent_model

        return {
            "status": "ready",
            "generation_provider": settings.generation_provider,
            "llm_provider": settings.llm_provider,
            "embedding_provider": settings.embedding_provider,
            "agents_sdk_enabled": settings.agents_sdk_enabled,
            "openai_agent_model": settings.openai_agent_model,
            "agent_llm_provider": resolve_agent_llm_provider(settings.agent_llm_provider),
            "agent_model": resolve_agent_model(settings.agent_llm_provider),
            "agent_llm_options": list_agent_llm_options(),
            "hf_agent_model": settings.hf_agent_model,
            "ollama_agent_model": settings.ollama_agent_model,
            "comfyui_base_url": settings.comfyui_base_url,
            "comfyui_url": (settings.comfyui_public_url or settings.comfyui_base_url).rstrip("/"),
        }

    # Serve built FE (SPA) from the same BE port — reliable when Vite :5174
    # port-forward resets in Cursor/Backend.AI browsers.
    fe_dist = Path(__file__).resolve().parents[2] / "fe" / "dist"
    if fe_dist.is_dir() and (fe_dist / "index.html").is_file():
        assets_dir = fe_dist / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="fe-assets")

        from fastapi.responses import FileResponse

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str):
            if full_path.startswith(("api/", "storage/", "docs", "openapi.json", "redoc")):
                from fastapi import HTTPException

                raise HTTPException(status_code=404, detail="Not found")
            candidate = fe_dist / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(fe_dist / "index.html")

    return app


app = create_app()
