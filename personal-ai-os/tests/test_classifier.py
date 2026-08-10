import pytest

from app.providers.fake_provider import FakeProvider
from app.routing.classifier import ClassificationError, TaskClassifier, TaskType


def test_classifies_research_request():
    llm = FakeProvider(canned_response='{"task_type": "research", "confidence": 0.9}')
    classifier = TaskClassifier(llm)

    result = classifier.classify("Explain RAG.")

    assert result.task_type == TaskType.RESEARCH
    assert result.confidence == 0.9


def test_classifies_analysis_request():
    llm = FakeProvider(canned_response='{"task_type": "analysis", "confidence": 0.85}')
    classifier = TaskClassifier(llm)

    result = classifier.classify("Compare RAG and fine-tuning.")

    assert result.task_type == TaskType.ANALYSIS


def test_classifies_planning_request():
    llm = FakeProvider(canned_response='{"task_type": "planning", "confidence": 0.8}')
    classifier = TaskClassifier(llm)

    result = classifier.classify("Create a 30-day plan for learning Docker.")

    assert result.task_type == TaskType.PLANNING


def test_low_confidence_becomes_unclear():
    llm = FakeProvider(canned_response='{"task_type": "research", "confidence": 0.2}')
    classifier = TaskClassifier(llm, confidence_threshold=0.5)

    result = classifier.classify("Do something useful.")

    assert result.task_type == TaskType.UNCLEAR


def test_malformed_json_raises_classification_error():
    llm = FakeProvider(canned_response="not json at all")
    classifier = TaskClassifier(llm)

    with pytest.raises(ClassificationError):
        classifier.classify("Explain RAG.")


def test_json_missing_fields_raises_classification_error():
    llm = FakeProvider(canned_response='{"task_type": "research"}')
    classifier = TaskClassifier(llm)

    with pytest.raises(ClassificationError):
        classifier.classify("Explain RAG.")


def test_extracts_json_wrapped_in_extra_text():
    llm = FakeProvider(
        canned_response='Sure, here you go:\n{"task_type": "research", "confidence": 0.9}\nHope that helps.'
    )
    classifier = TaskClassifier(llm)

    result = classifier.classify("Explain RAG.")

    assert result.task_type == TaskType.RESEARCH
