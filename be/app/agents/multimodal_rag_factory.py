"""Multimodal RAG agent factory (Vulcan-shaped).

Creates Agent + fixed tools when openai-agents is installed; otherwise a
mock descriptor used by the deterministic runner.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


class MultimodalRagAgentFactory:
    """Creates the Multimodal RAG agent + tools.

    Invariants:
    - Fixed tools only (no free-form code exec).
    - Never invents asset_id / timestamps.
    - Never approves assets or completes generation jobs.
    """

    AGENT_ID = "multimodal-rag"
    TOOL_NAMES = ("multimodal_search", "get_asset_content", "get_video_segment")

    @classmethod
    def create(
        cls,
        *,
        runtime: str = "mock",
        db: Session | None = None,
        project_id: int | None = None,
        media_type: str = "any",
    ) -> Any:
        if runtime == "openai-agents":
            return cls._create_live_agent(db=db, project_id=project_id, media_type=media_type)
        return {
            "agent_id": cls.AGENT_ID,
            "runtime": "mock",
            "tools": list(cls.TOOL_NAMES),
        }

    @classmethod
    def _create_live_agent(
        cls,
        *,
        db: Session | None,
        project_id: int | None,
        media_type: str,
    ) -> Any:
        from app.agents.live_runner import _build_tools
        from app.config import get_settings

        try:
            from agents import Agent  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "openai-agents is not installed; use LLM_PROVIDER=mock or install "
                "the [agents] extra"
            ) from exc

        settings = get_settings()
        tools = _build_tools(db, project_id=project_id, media_type=media_type) if db else []
        return Agent(
            name="Multimodal RAG",
            model=settings.openai_agent_model,
            instructions=(
                "You search approved production stills and video. "
                "Always cite cite_key for media claims. "
                "Distinguish image vs video. Never invent asset ids or timecodes. "
                "Never approve, reject, or generate assets."
            ),
            tools=tools,
        )
