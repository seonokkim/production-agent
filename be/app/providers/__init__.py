from app.config import get_settings
from app.providers.base import GenerationProvider
from app.providers.comfyui import ComfyUIProvider
from app.providers.embedding_base import EmbeddingProvider
from app.providers.embedding_mock import MockEmbeddingProvider
from app.providers.marengo import MarengoEmbeddingProvider
from app.providers.mock import MockProvider


def get_generation_provider() -> GenerationProvider:
    settings = get_settings()
    if settings.generation_provider == "comfyui":
        return ComfyUIProvider()
    return MockProvider()


def get_embedding_provider(provider: str | None = None) -> EmbeddingProvider:
    """Return embedding provider.

    `provider` optional override: ``mock`` | ``marengo`` | ``None`` (use settings).
    """
    settings = get_settings()
    choice = (provider or settings.embedding_provider or "mock").strip().lower()
    if choice in {"marengo", "twelvelabs", "twelve_labs", "twelve-labs"}:
        return MarengoEmbeddingProvider()
    return MockEmbeddingProvider()
