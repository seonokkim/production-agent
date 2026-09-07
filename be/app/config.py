from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "Production Agent"
    database_url: str = f"sqlite:///{ROOT_DIR / 'data' / 'production_agent.db'}"
    generation_provider: str = "mock"
    comfyui_base_url: str = "http://127.0.0.1:8188"
    asset_storage_path: str = str(ROOT_DIR / "storage")
    llm_provider: str = "mock"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    poll_interval_seconds: int = 2
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    comfy_workflows_dir: str = str(ROOT_DIR / "comfy" / "workflows")
    comfy_node_map_dir: str = str(ROOT_DIR / "comfy" / "node_map")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def model_post_init(self, __context) -> None:
        # Resolve relative sqlite paths against the repository root.
        if self.database_url.startswith("sqlite:///./"):
            rel = self.database_url.removeprefix("sqlite:///./")
            object.__setattr__(
                self, "database_url", f"sqlite:///{(ROOT_DIR / rel).resolve()}"
            )
        if not Path(self.asset_storage_path).is_absolute():
            object.__setattr__(
                self, "asset_storage_path", str((ROOT_DIR / self.asset_storage_path).resolve())
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
