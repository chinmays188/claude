import json
from pathlib import Path

EXAMPLES_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "multimodal_examples.json"


def _load():
    return json.loads(EXAMPLES_PATH.read_text())


def test_examples_file_has_all_4_input_kinds():
    data = _load()
    assert set(data.keys()) == {"text", "image", "pdf", "audio"}


def test_text_example_has_no_conversion():
    data = _load()
    assert data["text"]["extracted_text"] is None
    assert data["text"]["multimodal_model"] is None
    assert data["text"]["result"]["outcome"] == "answered"


def test_image_and_audio_examples_used_a_real_distinct_multimodal_model():
    data = _load()
    for kind in ("image", "audio"):
        assert data[kind]["extracted_text"]
        assert data[kind]["multimodal_model"] == "gemini-3.5-flash"


def test_audio_example_transcript_is_real_text_not_placeholder():
    data = _load()
    transcript = data["audio"]["extracted_text"]
    assert "RAG" in transcript or "fine tuning" in transcript.lower()


def test_examples_have_real_result_shape():
    data = _load()
    for kind, example in data.items():
        result = example["result"]
        assert result["outcome"] in ("answered", "clarification_needed")
        if result["outcome"] == "answered":
            assert result["output"]
        else:
            assert result["message"]
