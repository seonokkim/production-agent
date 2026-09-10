"""Model provider adapter for OpenAI Agents SDK.

Supports:
- openai — native OpenAI models (gpt-4o-mini, …)
- ollama — OpenAI-compatible local endpoint (Qwen3-8B via Ollama)
- hf — Hugging Face–downloaded weights served via local OpenAI-compatible /v1
- mock — deterministic runner (no LLM)

Live path keeps the openai-agents SDK surface; Ollama/HF use
OpenAIChatCompletionsModel + AsyncOpenAI(base_url=…).
"""

from __future__ import annotations

from typing import Any

from app.config import get_settings

# Catalog shown to FE /ready — ids are stable for API selection.
AGENT_LLM_OPTIONS: list[dict[str, str]] = [
    {
        "id": "openai",
        "label": "OpenAI (SDK)",
        "default_model": "gpt-4o-mini",
        "notes": "Requires OPENAI_API_KEY; Agents SDK native",
    },
    {
        "id": "ollama",
        "label": "Ollama (Qwen3-8B)",
        "default_model": "qwen3:8b",
        "notes": "Local Ollama OpenAI-compatible /v1 — agent/tool-capable Qwen3",
    },
    {
        "id": "hf",
        "label": "Hugging Face (Qwen3-8B)",
        "default_model": "Qwen/Qwen3-8B",
        "notes": "Weights under models/ via HF_TOKEN; served at HF_LLM_BASE_URL",
    },
    {
        "id": "mock",
        "label": "Mock (deterministic)",
        "default_model": "mock",
        "notes": "No external LLM; cite-grounded compose only",
    },
]


def agents_sdk_available() -> bool:
    try:
        import agents  # noqa: F401

        return True
    except ImportError:
        return False


def resolve_agent_llm_provider(override: str | None = None) -> str:
    settings = get_settings()
    raw = (override or settings.agent_llm_provider or settings.llm_provider or "mock").strip().lower()
    if raw in {"openai", "ollama", "hf", "huggingface", "mock"}:
        return "hf" if raw in {"hf", "huggingface"} else raw
    if raw in {"qwen", "qwen3", "qwen3:8b", "local"}:
        return "ollama"
    return "mock"


def resolve_agent_model(provider: str | None = None, override: str | None = None) -> str:
    settings = get_settings()
    if override and override.strip():
        return override.strip()
    prov = resolve_agent_llm_provider(provider)
    if prov == "ollama":
        return (settings.ollama_agent_model or "qwen3:8b").strip()
    if prov == "hf":
        return (settings.hf_agent_model or "Qwen/Qwen3-8B").strip()
    if prov == "openai":
        return (settings.openai_agent_model or settings.llm_model or "gpt-4o-mini").strip()
    return "mock"


def should_use_live_agents(provider: str | None = None) -> bool:
    settings = get_settings()
    if not settings.agents_sdk_enabled:
        return False
    if not agents_sdk_available():
        return False
    prov = resolve_agent_llm_provider(provider)
    if prov == "mock":
        return False
    if prov == "openai":
        return bool(settings.openai_api_key)
    if prov == "ollama":
        return bool(settings.ollama_base_url)
    if prov == "hf":
        return bool(settings.hf_llm_base_url)
    return False


def resolve_runtime_label(provider: str | None = None) -> str:
    prov = resolve_agent_llm_provider(provider)
    if not should_use_live_agents(prov):
        return "mock"
    if prov == "ollama":
        return "ollama-agents"
    if prov == "hf":
        return "hf-agents"
    return "openai-agents"


def _openai_compatible_base(url: str) -> str:
    base = url.rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return base


def build_agent_model(provider: str | None = None, model: str | None = None) -> Any:
    """Return a model string (OpenAI) or OpenAIChatCompletionsModel (Ollama/HF)."""
    from agents import OpenAIChatCompletionsModel  # type: ignore
    from openai import AsyncOpenAI

    settings = get_settings()
    prov = resolve_agent_llm_provider(provider)
    model_name = resolve_agent_model(prov, model)

    if prov == "ollama":
        client = AsyncOpenAI(
            base_url=_openai_compatible_base(settings.ollama_base_url),
            api_key=settings.ollama_api_key or "ollama",
        )
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)

    if prov == "hf":
        client = AsyncOpenAI(
            base_url=_openai_compatible_base(settings.hf_llm_base_url),
            api_key=settings.hf_llm_api_key or "hf-local",
        )
        # Local server registers the model under HF_AGENT_MODEL id (repo id or short name).
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)

    # OpenAI native — Agents SDK accepts model id string when OPENAI_API_KEY is set.
    return model_name


def list_agent_llm_options() -> list[dict[str, Any]]:
    settings = get_settings()
    out: list[dict[str, Any]] = []
    for opt in AGENT_LLM_OPTIONS:
        row: dict[str, Any] = dict(opt)
        if opt["id"] == "openai":
            row["default_model"] = settings.openai_agent_model or opt["default_model"]
            row["available"] = bool(settings.openai_api_key)
        elif opt["id"] == "ollama":
            row["default_model"] = settings.ollama_agent_model or opt["default_model"]
            row["available"] = bool(settings.ollama_base_url)
        elif opt["id"] == "hf":
            row["default_model"] = settings.hf_agent_model or opt["default_model"]
            row["available"] = bool(settings.hf_llm_base_url)
            row["local_dir"] = settings.hf_model_dir
        else:
            row["available"] = True
        out.append(row)
    return out


def chat_completions_endpoint(provider: str | None = None) -> tuple[str, str, str]:
    """Return (base_url_with_v1, api_key, model) for plain chat (shot-spec LLM)."""
    settings = get_settings()
    prov = resolve_agent_llm_provider(provider)
    model = resolve_agent_model(prov)
    if prov == "openai":
        return "https://api.openai.com/v1", settings.openai_api_key, model
    if prov == "ollama":
        return (
            _openai_compatible_base(settings.ollama_base_url),
            settings.ollama_api_key or "ollama",
            model,
        )
    if prov == "hf":
        return (
            _openai_compatible_base(settings.hf_llm_base_url),
            settings.hf_llm_api_key or "hf-local",
            model,
        )
    return "", "", "mock"
