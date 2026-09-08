"""Model provider adapter for OpenAI Agents SDK.

Live path wires when LLM_PROVIDER=openai and agents package is installed.
Mock path stays import-safe for CI without OPENAI_API_KEY.
"""

from __future__ import annotations

from app.config import get_settings


def agents_sdk_available() -> bool:
    try:
        import agents  # noqa: F401

        return True
    except ImportError:
        return False


def should_use_live_agents() -> bool:
    settings = get_settings()
    if not settings.agents_sdk_enabled:
        return False
    if settings.llm_provider != "openai":
        return False
    if not settings.openai_api_key:
        return False
    return agents_sdk_available()


def resolve_runtime_label() -> str:
    return "openai-agents" if should_use_live_agents() else "mock"
