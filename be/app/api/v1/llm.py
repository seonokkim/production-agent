"""LLM provider catalog + probe endpoints."""

from __future__ import annotations

import httpx
from fastapi import APIRouter

from app.agents.model_provider import (
    chat_completions_endpoint,
    list_agent_llm_options,
    resolve_agent_llm_provider,
    resolve_agent_model,
)
from app.config import get_settings
from app.schemas import LlmOption, LlmOptionsResponse

router = APIRouter(tags=["llm"])


@router.get("/llm/options", response_model=LlmOptionsResponse)
def llm_options():
    settings = get_settings()
    options = [LlmOption.model_validate(o) for o in list_agent_llm_options()]
    default_provider = resolve_agent_llm_provider(settings.agent_llm_provider)
    return LlmOptionsResponse(
        default_provider=default_provider,
        default_model=resolve_agent_model(default_provider),
        options=options,
    )


@router.get("/llm/probe/{provider}")
def llm_probe(provider: str):
    """Lightweight readiness probe for a provider (no generation)."""
    settings = get_settings()
    prov = resolve_agent_llm_provider(provider)
    model = resolve_agent_model(prov)
    if prov == "mock":
        return {"provider": prov, "model": model, "ok": True, "detail": "mock always ready"}
    if prov == "openai":
        return {
            "provider": prov,
            "model": model,
            "ok": bool(settings.openai_api_key),
            "detail": "key set" if settings.openai_api_key else "OPENAI_API_KEY missing",
        }
    base, key, _ = chat_completions_endpoint(prov)
    if not base:
        return {"provider": prov, "model": model, "ok": False, "detail": "no endpoint"}
    try:
        with httpx.Client(timeout=5.0) as client:
            # Prefer /models; some servers only expose chat.
            r = client.get(f"{base.rstrip('/')}/models", headers={"Authorization": f"Bearer {key}"})
            if r.status_code >= 400:
                r = client.get(base.rstrip("/").removesuffix("/v1") + "/health")
            ok = r.status_code < 500
            return {
                "provider": prov,
                "model": model,
                "ok": ok,
                "status_code": r.status_code,
                "detail": (r.text or "")[:200],
            }
    except Exception as exc:  # noqa: BLE001
        return {"provider": prov, "model": model, "ok": False, "detail": str(exc)[:200]}
