import time

from services.orchestrator.metrics import MetricsStore


def test_metrics_summary_aggregates_current_window():
    store = MetricsStore()
    store.record(model="main-llm", latency_ms=100, ok=True)
    store.record(model="main-llm", latency_ms=300, ok=True)
    store.record(model="coding", latency_ms=200, ok=False)

    summary = store.summary(window_seconds=3600)
    assert summary["current"]["requests"] == 3
    assert summary["current"]["avg_latency_ms"] == 200.0
    assert summary["current"]["error_rate"] == round(1 / 3, 4)
    assert summary["by_model"]["main-llm"] == 2
    assert sum(summary["series"]) == 3


def test_metrics_delta_is_none_without_baseline():
    store = MetricsStore()
    store.record(model="m", latency_ms=100, ok=True)
    summary = store.summary(window_seconds=3600)
    # No events in the previous window -> honest null delta, not a fabricated number.
    assert summary["delta_pct"]["requests"] is None


def test_metrics_delta_computed_against_previous_window():
    store = MetricsStore()
    now = time.time()
    # 1 event in the previous window, 2 in the current window.
    store.events.appendleft({"at": now - 5400, "model": "m", "latency_ms": 100.0, "ok": True})
    store.events.appendleft({"at": now - 100, "model": "m", "latency_ms": 100.0, "ok": True})
    store.events.appendleft({"at": now - 50, "model": "m", "latency_ms": 100.0, "ok": True})
    summary = store.summary(window_seconds=3600)
    assert summary["current"]["requests"] == 2
    assert summary["previous"]["requests"] == 1
    assert summary["delta_pct"]["requests"] == 100.0
