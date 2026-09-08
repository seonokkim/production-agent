"""Static agent catalog for Multimodal RAG (OpenAI Agents)."""

from __future__ import annotations

from app.schemas import AgentCatalogItem

MULTIMODAL_RAG_AGENT_ID = "multimodal-rag"

_CATALOG: list[AgentCatalogItem] = [
    AgentCatalogItem(
        agent_id=MULTIMODAL_RAG_AGENT_ID,
        type="knowledge",
        catalog_surface="knowledge",
        display_name_ko="멀티모달 RAG",
        display_name_en="Multimodal RAG",
        collection_ids=["approved-assets-image", "approved-assets-video"],
        description=(
            "OpenAI Agents–backed search over approved production stills and video. "
            "Cites media; attach into SceneFlow. Never approves or generates."
        ),
    )
]


def list_agents() -> list[AgentCatalogItem]:
    return list(_CATALOG)


def get_agent(agent_id: str) -> AgentCatalogItem | None:
    for item in _CATALOG:
        if item.agent_id == agent_id:
            return item
    return None
