"""LLM shot-spec suggestion with deterministic fallback."""

from __future__ import annotations

import json
import logging
import re

import httpx

from app.config import get_settings
from app.schemas import ShotSpecBase

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
        "cinematic still, late night abandoned factory, detective entering cautiously, "
        "rain and neon light through broken windows, tense cold atmosphere, medium wide, "
        "eye level, film still, 16:9"
    ),
    motion_prompt=(
        "slow tracking shot following behind the detective, subtle rain motion, "
        "flickering neon reflections, tense camera move"
    ),
)


class LLMProvider:
    def suggest_shot_spec(self, brief: str) -> ShotSpecBase:
        settings = get_settings()
        if settings.llm_provider == "mock" or not settings.openai_api_key:
            return self._deterministic_from_brief(brief)

        try:
            return self._openai_suggest(brief)
        except Exception:
            logger.exception("LLM suggestion failed; using deterministic fallback")
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
            # Keep original brief words visible in prompts for demo transparency.
            snippet = re.sub(r"\s+", " ", brief.strip())[:180]
            base.visual_prompt = f"{base.visual_prompt}. Scene brief: {snippet}"
            base.motion_prompt = f"{base.motion_prompt}. Scene brief: {snippet}"
        return base

    def _openai_suggest(self, brief: str) -> ShotSpecBase:
        settings = get_settings()
        system = (
            "You convert a drama scene brief into a structured shot specification. "
            "Return ONLY valid JSON with keys: location, time_of_day, subjects (array), "
            "action, shot_size, camera_angle, camera_motion, lighting, mood, "
            "visual_prompt, motion_prompt."
        )
        payload = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": brief},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        return ShotSpecBase.model_validate(data)
