from app.agents.orchestrator import Orchestrator
from app.api.voice_api import _build_orchestrator, _get_shared_semantic_cache
from app.caching.semantic_cache import SemanticCachingProvider


def test_build_orchestrator_wires_a_real_semantic_caching_classification_llm():
    """Found missing while investigating 'AI Cost & Latency Engineering':
    the real semantic cache had no real production wiring anywhere. This
    is the one that matters -- the long-running server's real
    orchestrator_factory."""
    orchestrator = _build_orchestrator()

    assert isinstance(orchestrator, Orchestrator)
    assert isinstance(orchestrator._router._domain_router._generator._llm, SemanticCachingProvider)


def test_shared_semantic_cache_is_genuinely_shared_across_calls():
    """Process-wide, not per-session -- confirmed by identity, not just
    equal contents."""
    cache_a = _get_shared_semantic_cache()
    cache_b = _get_shared_semantic_cache()

    assert cache_a is cache_b


def test_build_orchestrator_called_twice_shares_the_same_cache():
    orchestrator_1 = _build_orchestrator()
    orchestrator_2 = _build_orchestrator()

    cache_1 = orchestrator_1._router._domain_router._generator._llm._cache
    cache_2 = orchestrator_2._router._domain_router._generator._llm._cache

    assert cache_1 is cache_2
