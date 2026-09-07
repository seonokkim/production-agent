from app.config import get_settings
from app.providers.base import GenerationProvider
from app.providers.comfyui import ComfyUIProvider
from app.providers.mock import MockProvider


def get_generation_provider() -> GenerationProvider:
    settings = get_settings()
    if settings.generation_provider == "comfyui":
        return ComfyUIProvider()
    return MockProvider()
