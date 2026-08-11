from app.multimodal.base import MediaType
from tests.fakes.fake_multimodal import FakeMultimodalProvider


def test_understand_returns_response():
    provider = FakeMultimodalProvider(canned_response="This is a TypeError on line 42.")

    result = provider.understand("What's wrong?", b"fake-image-bytes", MediaType.SCREENSHOT, "image/png")

    assert result == "This is a TypeError on line 42."


def test_understand_records_call_details():
    provider = FakeMultimodalProvider()

    provider.understand("Extract the table.", b"12345", MediaType.PDF, "application/pdf")

    assert provider.last_call["media_type"] == MediaType.PDF
    assert provider.last_call["mime_type"] == "application/pdf"
    assert provider.last_call["media_bytes_len"] == 5
