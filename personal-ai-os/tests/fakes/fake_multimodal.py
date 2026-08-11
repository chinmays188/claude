from app.multimodal.base import MediaType, MultimodalProvider


class FakeMultimodalProvider(MultimodalProvider):
    def __init__(self, canned_response: str = "fake multimodal response"):
        self._canned_response = canned_response
        self.last_call: dict | None = None

    def understand(self, prompt: str, media_bytes: bytes, media_type: MediaType, mime_type: str) -> str:
        self.last_call = {
            "prompt": prompt, "media_bytes_len": len(media_bytes),
            "media_type": media_type, "mime_type": mime_type,
        }
        return self._canned_response
