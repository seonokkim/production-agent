"""LLM shot-spec suggestion with deterministic fallback.

Supports openai / ollama / hf (OpenAI-compatible) / mock via per-call provider override.
"""

from __future__ import annotations

import json
import logging
import re

import httpx

from app.agents.model_provider import chat_completions_endpoint, resolve_agent_llm_provider
from app.config import get_settings
from app.schemas import ShotSpecBase
from app.services.style_lock import LLM_STYLE_SYSTEM_EXTRA, STYLE_POSITIVE

logger = logging.getLogger(__name__)

DEMO_FALLBACK = ShotSpecBase(
    location="abandoned factory",
    time_of_day="night",
    subjects=["detective"],
    action="enters the factory cautiously",
    shot_size="medium wide",
    camera_angle="eye level",
    camera_motion="slow tracking shot",
    lighting="dark interior with neon reflections",
    mood="suspenseful",
    visual_prompt=(
        f"{STYLE_POSITIVE}, late night abandoned factory, detective entering cautiously, "
        "rain and neon light through broken windows, tense cold atmosphere, medium wide, "
        "eye level"
    ),
    motion_prompt=(
        f"{STYLE_POSITIVE}, live-action continuous shot, slow tracking shot following behind "
        "the detective, subtle rain motion, flickering neon reflections, natural motion, "
        "no stylization"
    ),
)


class LLMProvider:
    def suggest_shot_spec(
        self,
        brief: str,
        *,
        llm_provider: str | None = None,
        llm_model: str | None = None,
    ) -> ShotSpecBase:
        prov = resolve_agent_llm_provider(llm_provider)
        if prov == "mock":
            return self._deterministic_from_brief(brief)

        try:
            return self._chat_suggest(brief, provider=prov, model=llm_model)
        except Exception:
            logger.exception(
                "LLM suggestion failed (provider=%s); using deterministic fallback", prov
            )
            return self._deterministic_from_brief(brief)

    def _deterministic_from_brief(self, brief: str) -> ShotSpecBase:
        text = (brief or "").lower()
        base = DEMO_FALLBACK.model_copy(deep=True)
        if "subway" in text:
            base.location = "subway platform"
            base.lighting = "fluorescent flicker and cold concrete"
        if "day" in text and "night" not in text:
            base.time_of_day = "day"
        if "woman" in text or "mina" in text:
            base.subjects = ["Mina"]
        if brief.strip():
            snippet = re.sub(r"\s+", " ", brief.strip())[:180]
            base.visual_prompt = f"{base.visual_prompt}. Scene brief: {snippet}"
            base.motion_prompt = f"{base.motion_prompt}. Scene brief: {snippet}"
        return base

    def _chat_suggest(
        self,
        brief: str,
        *,
        provider: str,
        model: str | None = None,
    ) -> ShotSpecBase:
        base_url, api_key, default_model = chat_completions_endpoint(provider)
        if not base_url or not api_key:
            return self._deterministic_from_brief(brief)
        model_name = (model or default_model).strip()
        system = (
            "You convert a drama scene brief into a structured shot specification. "
            "Return ONLY valid JSON with keys: location, time_of_day, subjects (array), "
            "action, shot_size, camera_angle, camera_motion, lighting, mood, "
            "visual_prompt, motion_prompt. "
            + LLM_STYLE_SYSTEM_EXTRA
        )
        payload: dict = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": brief},
            ],
            "temperature": 0.2,
        }
        # OpenAI supports response_format; local Qwen servers may not.
        if provider == "openai":
            payload["response_format"] = {"type": "json_object"}

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

        # Strip optional <think>…</think> blocks from Qwen3 thinking mode.
        if isinstance(content, str) and "</think>" in content:
            content = content.split("</think>", 1)[-1].strip()
        # Extract JSON object if model wrapped it in markdown.
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        data = json.loads(text)
        return ShotSpecBase.model_validate(data)
