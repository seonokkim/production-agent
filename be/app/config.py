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
    # This repo defaults to isolated ComfyUI :8189 (sibling / shared uses :8188).
    comfyui_base_url: str = "http://127.0.0.1:8189"
    # Optional browser-reachable URL when clients cannot open 127.0.0.1 (e.g. port-forward).
    comfyui_public_url: str = ""
    # Must match the isolated ComfyUI --base-directory/.../input (see scripts/start_comfyui_isolated.sh).
    comfyui_input_dir: str = str(ROOT_DIR / "comfy_runtime" / "input")
    asset_storage_path: str = str(ROOT_DIR / "storage")
    asset_storage_provider: str = "local"  # local | s3
    asset_landing_path: str = str(ROOT_DIR / "storage" / "landing")
    aws_s3_bucket: str = ""
    aws_region: str = "ap-northeast-2"
    n8n_review_webhook_url: str = ""
    llm_provider: str = "mock"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    poll_interval_seconds: int = 2
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    comfy_workflows_dir: str = str(ROOT_DIR / "comfy" / "workflows")
    comfy_node_map_dir: str = str(ROOT_DIR / "comfy" / "node_map")
    # P1 — Approved Reference Retrieval
    embedding_provider: str = "mock"
    twelve_labs_api_key: str = ""
    embedding_model: str = "marengo3.5"
    embedding_dim: int = 512
    # P2 — Multimodal RAG (OpenAI Agents SDK + OpenAI-compatible local)
    agents_sdk_enabled: bool = True
    openai_agent_model: str = "gpt-4o-mini"
    # Agent LLM backend: openai | ollama | hf | mock
    agent_llm_provider: str = "openai"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_api_key: str = "ollama"
    # Qwen3-8B: latest agent/tool-capable Qwen on Ollama
    ollama_agent_model: str = "qwen3:8b"
    # Hugging Face local serve (download via HF_TOKEN → models/, serve on :8002)
    hf_token: str = ""
    hf_agent_model: str = "Qwen/Qwen3-8B"
    hf_model_dir: str = str(ROOT_DIR / "models" / "Qwen3-8B")
    hf_llm_base_url: str = "http://127.0.0.1:8002"
    hf_llm_api_key: str = "hf-local"

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
        if not Path(self.asset_landing_path).is_absolute():
            object.__setattr__(
                self, "asset_landing_path", str((ROOT_DIR / self.asset_landing_path).resolve())
            )
        if self.comfyui_input_dir and not Path(self.comfyui_input_dir).is_absolute():
            object.__setattr__(
                self, "comfyui_input_dir", str((ROOT_DIR / self.comfyui_input_dir).resolve())
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
