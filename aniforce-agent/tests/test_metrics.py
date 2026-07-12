from prometheus_client import CollectorRegistry, Counter

from app.core import metrics


def test_observe_tokens_accepts_runtime_usage_contract(monkeypatch) -> None:
    registry = CollectorRegistry()
    token_counter = Counter(
        "test_agent_tokens_total",
        "test",
        ("execution_kind", "token_type"),
        registry=registry,
    )
    monkeypatch.setattr(metrics, "AGENT_TOKENS", token_counter)

    metrics.observe_tokens(
        "initial",
        {"input": 100, "output": 20, "cacheRead": 10, "cacheWrite": 0, "totalTokens": 120},
    )

    samples = {
        (sample.labels["execution_kind"], sample.labels["token_type"]): sample.value
        for metric in registry.collect()
        for sample in metric.samples
        if sample.name == "test_agent_tokens_total"
    }
    assert samples[("initial", "input")] == 100
    assert samples[("initial", "output")] == 20
    assert samples[("initial", "cache_read")] == 10
