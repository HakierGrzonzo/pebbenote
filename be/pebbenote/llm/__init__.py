from typing import Any

from ..config import AiProviderKinds, settings
from .base import AIAdapter, AIProvider
from .ollama import OllamaAdapter

providers: dict[AiProviderKinds, Any] = {
    "Ollama": OllamaAdapter,
    "Null": AIAdapter,
}

ai_provider = AIProvider(providers[settings.AI_PROVIDER])
