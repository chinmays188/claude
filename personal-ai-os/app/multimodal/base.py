from abc import ABC, abstractmethod
from enum import Enum


class MediaType(str, Enum):
    IMAGE = "image"
    SCREENSHOT = "screenshot"
    PDF = "pdf"


class MultimodalProvider(ABC):
    """Provider-family abstraction for image/screenshot/PDF understanding,
    mirroring Section 6's EmbeddingProvider/VoiceProvider pattern — no
    application code should depend on a specific multimodal vendor directly."""

    @abstractmethod
    def understand(self, prompt: str, media_bytes: bytes, media_type: MediaType, mime_type: str) -> str:
        """Return a text response grounded in both the prompt and the media."""
